#!/usr/bin/env python3
"""Compute fixed triage groups/dates from source-linked interpreted facts.

Input is {"tasks": [...]}; required fields are documented by FIELDS below.
Booleans may be null, enums include unknown, and timestamps are offset-aware or
null. Complete history distinguishes absent messages from unobserved messages.
This helper does not prove evidence completeness, interpret text, or authorize
effects. runs.py binds these assertions to the actual Task/mail collection.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FIELDS = {"task_id", "mailbox", "thread_id", "existing_draft", "mail_complete",
          "relationship", "last_sent_at", "last_reply_at", "held_meeting_at",
          "meeting_moved", "internal_prep", "unanswered_count", "recipient",
          "cooldown_until", "channel", "bodies_complete", "source_refs"}
BOOLS = ("existing_draft", "mail_complete", "meeting_moved", "internal_prep", "bodies_complete")
DAY_KEYS = ("sent_mail_hold_days_cold", "sent_mail_hold_days_active", "next_date_days_active",
            "next_date_days_cold", "cooldown_days")


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("expected offset-aware timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("expected offset-aware timestamp")
    return parsed


def evaluate(data, policy, as_of):
    """Return one decision per valid Task and contextual input errors."""
    errors, decisions = [], []
    result = {"errors": errors, "complete": False, "tasks": decisions, "task_ids": []}
    try:
        zone = ZoneInfo(policy["identity"]["timezone"])
        now = _timestamp(as_of) if isinstance(as_of, str) else as_of
        if not isinstance(now, dt.datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("as_of must be offset-aware")
        today = now.astimezone(zone).date()
        followup = policy["followup"]
        for key in DAY_KEYS + ("recycle_after_unanswered",):
            value = followup[key]
            if type(value) is not int or value < (1 if key == "recycle_after_unanswered" else 0):
                raise ValueError("invalid followup." + key)
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        errors.append("triage policy/time: " + str(exc))
        return result
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        errors.append("triage: expected object with tasks array")
        return result
    seen, drafts = set(), {}
    for index, task in enumerate(data["tasks"]):
        label = "tasks[%d]" % index
        before = len(errors)
        if not isinstance(task, dict):
            errors.append(label + ": expected object")
            continue
        missing = FIELDS - task.keys()
        if missing:
            errors.append(label + ": missing " + ", ".join(sorted(missing)))
        unknown = task.keys() - FIELDS - {"draft", "contact_email"}
        if unknown:
            errors.append(label + ": unsupported fields " + ", ".join(sorted(unknown)))
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in seen:
            errors.append(label + ": missing or duplicate task_id")
        else:
            seen.add(task_id)
            result["task_ids"].append(task_id)
        if not isinstance(task.get("mailbox"), str) or not task["mailbox"].strip():
            errors.append(label + ": mailbox required")
        if "contact_email" in task and (not isinstance(task["contact_email"], str) or not task["contact_email"].strip() or "@" not in task["contact_email"]):
            errors.append(label + ": contact_email must identify the selected correspondent")
        if task.get("thread_id") is not None and (not isinstance(task["thread_id"], str) or not task["thread_id"].strip()):
            errors.append(label + ": thread_id must be string or null")
        for key in BOOLS:
            if task.get(key) is not None and type(task[key]) is not bool:
                errors.append(label + ": " + key + " must be boolean or null")
        for key, choices in (("relationship", ("active", "cold", "unknown")),
                             ("recipient", ("confirmed", "unconfirmed", "unknown")),
                             ("channel", ("email", "linkedin_only", "unknown"))):
            if task.get(key) not in choices:
                errors.append(label + ": invalid " + key)
        count = task.get("unanswered_count")
        if count is not None and (type(count) is not int or count < 0):
            errors.append(label + ": unanswered_count must be nonnegative integer or null")
        refs = task.get("source_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs):
            errors.append(label + ": nonempty source_refs required")
        times = {}
        for key in ("last_sent_at", "last_reply_at", "held_meeting_at"):
            try:
                times[key] = _timestamp(task[key]) if task.get(key) is not None else None
                if times[key] is not None and times[key] > now:
                    raise ValueError("future sent/reply/held fact")
            except (TypeError, ValueError) as exc:
                errors.append(label + "." + key + ": " + str(exc))
        try:
            cooldown = dt.date.fromisoformat(task["cooldown_until"]) if task.get("cooldown_until") is not None else None
        except (TypeError, ValueError):
            errors.append(label + ": invalid cooldown_until")
            cooldown = None
        if task.get("relationship") == "cold" and (times.get("last_reply_at") or times.get("held_meeting_at")):
            errors.append(label + ": cold conflicts with confirmed substantive reply/held meeting")
        draft = task.get("draft")
        if draft is not None:
            required = {"to", "cc", "bcc", "subject", "body", "attachments"}
            if not isinstance(draft, dict) or set(draft) != required:
                errors.append(label + ": draft needs exact to/cc/bcc/subject/body/attachments")
            elif any(not isinstance(draft[k], list) for k in ("to", "cc", "bcc", "attachments")) or any(not isinstance(draft[k], str) for k in ("subject", "body")):
                errors.append(label + ": invalid draft field types")
        if len(errors) != before:
            continue
        sent, reply, held = (times[k] for k in ("last_sent_at", "last_reply_at", "held_meeting_at"))
        decision = {"task_id": task_id, "group": "hold", "reason": "", "proposed_date": None,
                    "cooldown_until": None, "source_refs": refs}
        complete = task["mail_complete"] is True
        relation = task["relationship"]
        newer = complete and any(t is not None and (sent is None or t > sent) for t in (reply, held))
        if task["existing_draft"] is True:
            decision.update(group="held_existing_draft", reason="Existing draft; inspect and retain it.")
        elif task["internal_prep"] is True or task["meeting_moved"] is True or newer:
            decision.update(group="manual", reason="Verified response/meeting or reviewed manual task; choose action in review.")
        elif task["existing_draft"] is None:
            decision["reason"] = "Existing-draft coverage unknown."
        elif relation == "cold" and complete and count is not None and count >= followup["recycle_after_unanswered"]:
            next_date = (today + dt.timedelta(days=followup["cooldown_days"])).isoformat()
            decision.update(group="recycle", reason="Cold contact meets unanswered threshold; review Push or Recycle.",
                            proposed_date=next_date, cooldown_until=next_date)
        else:
            reasons, releases, unresolved = [], [], False
            for bad, reason in ((not complete, "Mail history incomplete"),
                                (relation == "unknown", "Relationship unknown"),
                                (task["recipient"] != "confirmed", "Recipient unconfirmed"),
                                (task["channel"] != "email", "Email channel unavailable or unknown"),
                                (task["bodies_complete"] is not True, "Relevant full bodies unavailable"),
                                (sent is None, "No established prior outbound for this follow-up"),
                                (task["thread_id"] is None, "Selected thread unavailable"),
                                (task["meeting_moved"] is None or task["internal_prep"] is None, "Manual-response condition unknown"),
                                (relation == "cold" and count is None, "Unanswered count unknown")):
                if bad:
                    reasons.append(reason)
                    unresolved = True
            if sent is not None and relation in ("active", "cold"):
                release = sent.astimezone(zone).date() + dt.timedelta(days=followup["sent_mail_hold_days_" + relation])
                if today < release:
                    reasons.append("Recent outbound hold window")
                    releases.append(release)
            if cooldown and today < cooldown:
                reasons.append("Existing cooldown")
                releases.append(cooldown)
            if reasons:
                decision["reason"] = "; ".join(reasons) + "."
                if releases and not unresolved:
                    decision["proposed_date"] = max(releases).isoformat()
            else:
                decision.update(group="draft", reason="Verified follow-up evidence; review exact draft.",
                                proposed_date=(today + dt.timedelta(days=followup["next_date_days_" + relation])).isoformat())
        decisions.append(decision)
        if draft is not None and decision["group"] == "draft":
            key = (task["mailbox"], task["thread_id"])
            drafts.setdefault(key, []).append((decision, json.dumps(draft, sort_keys=True)))
    for rows in drafts.values():
        if len({payload for _, payload in rows}) > 1:
            errors.append("triage: conflicting reviewed drafts on the same mailbox/thread require reconciliation")
            for decision, _ in rows:
                decision.update(group="hold", reason="Conflicting draft proposals; reconcile recipients/content.", proposed_date=None)
        elif len(rows) > 1:
            ids = sorted(d["task_id"] for d, _ in rows)
            for decision, _ in rows:
                decision["shared_draft_task_ids"] = ids
    result["complete"] = not errors
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--policy", type=Path, default=Path("_shared/policy.json"))
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.input.read_text()), json.loads(args.policy.read_text()), args.as_of)
    except (OSError, ValueError) as exc:
        result = {"complete": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
