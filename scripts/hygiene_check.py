#!/usr/bin/env python3
"""Deterministic hygiene check for pipeline-review.

Usage: hygiene_check.py <opps.json> [--tasks tasks.json] [--events events.json]
                        [--policy PATH] [--today YYYY-MM-DD]
                        [--as-of ISO_DATETIME_WITH_OFFSET] [--json]

Inputs are saved CRM query outputs (Opportunity, Task, Event). For every
open deal in policy.pipeline.in_scope_stages it emits one line:
  triggers it can compute from CRM (policy.pipeline.triggers): next_passed,
    new_activity (inbound 'Email: <<' Task or elapsed Event after the newest note),
    blank_field, date_at_risk, stale
  blank required and conditional fields, next-step status, newest note date,
  last activity, next upcoming Event, open Tasks
Deals below the scope report only whether NextSteps is empty.
Events require end timestamps to count as elapsed. Elapsed does not prove held.
--today without --as-of uses local midnight, conservatively excluding same-day
events. Activity evidence retains record IDs and linkage for report verification.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


# Deprecated write format; retained only to read existing CRM records.
NEXT_RE = re.compile(
    r"^Next:\s*(?P<action>.+?)\s*\u00b7\s*(?P<owner>.+?)\s*\u00b7\s*(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\.?\s*$"
)
NOTE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4}) [A-Za-z][A-Za-z0-9_. -]* -")
DATED_NEXT_STEP_RE = re.compile(
    r"^(?P<written>\d{1,2}/\d{1,2}/\d{2,4}) [A-Za-z][A-Za-z0-9_. -]* -\s*(?P<action>.+)$"
)
NEXT_STEP_DUE_DATE_RE = re.compile(
    r"\b(?:on|by)\s+(?P<date>\d{1,2}/\d{1,2}(?:/\d{2,4})?)(?![\d/])",
    re.I,
)
INBOUND = "Email: <<"


@dataclass(frozen=True)
class ParsedNextStep:
    status: Literal["OK", "MISSING", "REVIEW"]
    action: str | None = None
    due_date: dt.date | None = None
    owner: str | None = None
    format: Literal["dated_sentence", "legacy"] | None = None
    review_reason: str | None = None


def parse_next_step_line(line: str) -> ParsedNextStep:
    """Extract deadlines conservatively; a written date or author is not a deadline or owner."""
    legacy = NEXT_RE.fullmatch(line)
    if legacy:
        try:
            deadline = parse_mdy(legacy["date"])
        except ValueError:
            return ParsedNextStep("REVIEW", format="legacy", review_reason="Invalid legacy due date")
        return ParsedNextStep(
            "OK", legacy["action"], deadline, legacy["owner"], "legacy"
        )

    dated = DATED_NEXT_STEP_RE.fullmatch(line)
    if not dated:
        return ParsedNextStep("MISSING")
    try:
        written = parse_mdy(dated["written"])
    except ValueError:
        return ParsedNextStep(
            "REVIEW", dated["action"], format="dated_sentence",
            review_reason="Invalid entry date",
        )
    matches = list(NEXT_STEP_DUE_DATE_RE.finditer(dated["action"]))
    if not matches:
        return ParsedNextStep(
            "REVIEW", dated["action"], format="dated_sentence",
            review_reason="No explicit on/by action due date; verify the sentence",
        )
    try:
        deadlines = {
            parse_mdy(
                match["date"] if match["date"].count("/") == 2
                else f"{match['date']}/{written.year}"
            )
            for match in matches
        }
    except ValueError:
        return ParsedNextStep(
            "REVIEW", dated["action"], format="dated_sentence",
            review_reason="Invalid action due date",
        )
    if len(deadlines) != 1:
        return ParsedNextStep(
            "REVIEW", dated["action"], format="dated_sentence",
            review_reason="Multiple possible action due dates; verify which is the deadline",
        )
    return ParsedNextStep(
        "OK", dated["action"], deadlines.pop(), format="dated_sentence"
    )


def load_records(path):
    if not path:
        return []
    d = json.loads(Path(path).read_text())
    r = d.get("result", d) if isinstance(d, dict) else d
    if isinstance(r, str):
        r = json.loads(r)
    if isinstance(r, dict):
        if r.get("error") or r.get("authenticated") is False:
            raise ValueError("failed CRM source: " + str(path))
        r = next((r[k] for k in ("records", "result", "data") if k in r), None)
    if not isinstance(r, list):
        raise ValueError("missing CRM records: " + str(path))
    return r


def parse_mdy(s):
    m, d, y = s.split("/")
    y = int(y)
    return dt.date(y + 2000 if y < 100 else y, int(m), int(d))


def parse_iso(s):
    return dt.date.fromisoformat(s[:10]) if s else None


def parse_activity_timestamp(value: str | None) -> dt.datetime | None:
    """Reject timestamps without offsets rather than inventing a timezone."""
    if not value:
        return None
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Activity timestamp must include a timezone offset")
    return parsed


def classify_event_timing(
    start: dt.datetime | None, end: dt.datetime | None, as_of: dt.datetime
) -> str:
    """A date or invitation alone cannot establish that a meeting has ended."""
    if start and end and end < start:
        return "timing_unknown"
    if start and start > as_of:
        return "upcoming"
    if end and end <= as_of:
        return "elapsed"
    if start and end and start <= as_of < end:
        return "in_progress"
    return "timing_unknown"


def activity_receipt(activity: dict | None) -> dict | None:
    """Retain the exact source record so summaries cannot silently change scope."""
    if activity is None:
        return None
    return {
        key: value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else value
        for key, value in activity.items()
    }


def clean_text(s):
    s = re.sub(r"<br\s*/?>|</p>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")


def is_blank(v):
    return v is None or v == "" or v is False or v == 0


def check(rec, pol, acts, today, as_of=None):
    pp = pol["pipeline"]
    stage = rec.get("StageName") or ""
    order = pp["stage_order"]
    stage_key = stage.split(" - ", 1)[0]
    so = order.index(stage_key) if stage_key in order else -1
    acct = (rec.get("Account") or {}).get("Name") or rec.get("AccountId") or ""
    text = clean_text(rec.get("NextSteps"))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = {"Id": rec.get("Id"), "Account": acct, "Stage": stage, "triggers": []}
    scope = set(pp["in_scope_stages"])

    if stage_key not in scope:
        out["next_steps_empty"] = not lines
        return out

    # required and conditional fields
    required = []
    for o, s in enumerate(order):
        if o <= so:
            required += pp["required_fields"].get(s) or []
    for c in pp.get("conditional_fields") or []:
        if all(rec.get(k) == v for k, v in (c.get("when") or {}).items()):
            required.append(c["field"])
    out["blank_fields"] = [f for f in required if is_blank(rec.get(f))]

    # Only the first entry is current; older dated entries remain history.
    parsed_next = parse_next_step_line(lines[0]) if lines else ParsedNextStep("MISSING")
    dup_next = sum(1 for ln in lines if NEXT_RE.match(ln))
    if dup_next > 1:
        out["duplicate_next_lines"] = dup_next
        if "blank_field" not in out["triggers"]:
            out["triggers"].append("blank_field")   # malformed NextSteps: more than one Next line
    out["next"] = parsed_next.status
    if parsed_next.format:
        out["next_format"] = parsed_next.format
    if parsed_next.review_reason:
        out["next_review_reason"] = parsed_next.review_reason
    if parsed_next.status == "OK":
        d = parsed_next.due_date
        assert d is not None
        out["next_action"] = parsed_next.action
        out["next_owner"] = parsed_next.owner
        out["next_date"] = d.isoformat()
        if d < today:
            out["next_passed_days"] = (today - d).days
            out["triggers"].append("next_passed")
    if (out["blank_fields"] or out["next"] != "OK") and "blank_field" not in out["triggers"]:
        out["triggers"].append("blank_field")

    notes = []
    for raw_date in NOTE_RE.findall(text):
        try:
            notes.append(parse_mdy(raw_date))
        except ValueError:
            continue  # A malformed entry must not abort every account's review.
    newest_note = max(notes) if notes else None
    out["newest_note"] = newest_note.isoformat() if newest_note else None

    # activity
    # Activity linked to the Opportunity or to its Account. The org email sync logs most Email Tasks on the Account.
    items, seen = [], set()
    for a in acts.get(rec.get("Id"), []) + acts.get(rec.get("AccountId"), []):
        k = a.get("id") or (a["date"], a["subject"], a["kind"])
        if k not in seen:
            seen.add(k); items.append(a)
    as_of = as_of or dt.datetime.combine(today, dt.time.min, dt.timezone.utc)
    for a in items:
        if a["kind"] == "event":
            a["timing"] = classify_event_timing(a.get("start"), a.get("end"), as_of)
    past = [
        a for a in items if a["date"] and a["date"] <= today
        and a["kind"] != "open_task"
        and (a["kind"] != "event" or a["timing"] == "elapsed")
    ]
    upcoming = [
        a for a in items if a["kind"] == "event"
        and (a["timing"] in ("upcoming", "in_progress")
             or (a["timing"] == "timing_unknown" and a["date"] and a["date"] > today))
    ]
    open_tasks = [a for a in items if a["kind"] == "open_task"]
    last = max(past, key=lambda a: a["date"]) if past else None
    nxt_ev = min(upcoming, key=lambda a: a["date"]) if upcoming else None
    out["last_activity"] = f"{last['date']} {last['subject']}" if last else None
    out["last_activity_evidence"] = activity_receipt(last)
    out["upcoming_event"] = f"{nxt_ev['date']} {nxt_ev['subject']}" if nxt_ev else None
    out["upcoming_event_evidence"] = activity_receipt(nxt_ev)
    out["unverified_events"] = [
        activity_receipt(a) for a in items
        if a["kind"] == "event" and a["timing"] in ("elapsed", "timing_unknown")
    ]
    out["open_tasks"] = [f"{a['date']} {a['subject']}" for a in open_tasks]
    # task_gap uses the action deadline, never the dated entry's written date.
    if out.get("next") == "OK" and "next_passed_days" not in out:
        nd = dt.date.fromisoformat(out["next_date"])
        out["task_gap"] = not any(a["date"] == nd for a in open_tasks)
    else:
        out["task_gap"] = False

    buyer = [a for a in past if a["kind"] in ("inbound", "event")]
    buyer = [a for a in buyer if newest_note is None or a["date"] > newest_note]
    if buyer:
        b = max(buyer, key=lambda a: a["date"])
        out["new_activity"] = f"{b['date']} {b['subject']}"
        out["new_activity_evidence"] = activity_receipt(b)
        out["triggers"].append("new_activity")

    close = parse_iso(rec.get("CloseDate"))
    if close and (close < today or (so < order.index(pp["close_warning_before_stage"]) and (close - today).days <= pp["close_warning_days"])):
        out["triggers"].append("date_at_risk")

    cutoff = today - dt.timedelta(days=pp["stale_days"])
    next_live = out.get("next") == "OK" and "next_passed_days" not in out
    if not any(a["date"] >= cutoff for a in past) and not upcoming and not next_live:
        out["triggers"].append("stale")
    return out


def index_activity(tasks, events, timezone=dt.timezone.utc):
    acts = defaultdict(list)
    for t in tasks:
        d = parse_iso(t.get("ActivityDate"))
        subj = t.get("Subject") or ""
        if not t.get("IsClosed", t.get("Status") == "Completed") and t.get("Status") != "Completed":
            kind = "open_task"
        elif subj.startswith(INBOUND):
            kind = "inbound"
        else:
            kind = "task"
        rec_ = {
            "id": t.get("Id"), "date": d, "subject": subj, "kind": kind,
            "what_id": t.get("WhatId"), "account_id": t.get("AccountId"),
            "contact": (t.get("Who") or {}).get("Name"),
        }
        acts[t.get("WhatId")].append(rec_)
        if t.get("AccountId") and t.get("AccountId") != t.get("WhatId"):
            acts[t.get("AccountId")].append(rec_)
    for e in events:
        start = parse_activity_timestamp(e.get("StartDateTime"))
        end = parse_activity_timestamp(e.get("EndDateTime"))
        d = start.astimezone(timezone).date() if start else parse_iso(e.get("ActivityDate"))
        ev = {
            "id": e.get("Id"), "date": d, "subject": e.get("Subject") or "", "kind": "event",
            "start": start, "end": end, "what_id": e.get("WhatId"),
            "account_id": e.get("AccountId"),
        }
        acts[e.get("WhatId")].append(ev)
        if e.get("AccountId") and e.get("AccountId") != e.get("WhatId"):
            acts[e.get("AccountId")].append(ev)
    return acts


def fmt(o):
    head = f"{o['Account']} | {o['Stage']} | {o['Id']}"
    if "next_steps_empty" in o:
        return f"{head} | out of scope | NextSteps {'EMPTY' if o['next_steps_empty'] else 'present'}"
    nxt = o["next"]
    if nxt == "OK":
        owner = o.get("next_owner")
        action = f"{owner}: {o['next_action']}" if owner else o["next_action"]
        nxt = f"OK {o['next_date']} ({action})"
        if "next_passed_days" in o:
            nxt += f" PASSED {o['next_passed_days']}d"
    parts = [
        head,
        "triggers: " + (", ".join(o["triggers"]) or "none"),
        "blank: " + (", ".join(o["blank_fields"]) or "none"),
        "next: " + nxt,
        "newest note: " + (o["newest_note"] or "none"),
        "last activity: " + (o["last_activity"] or "none"),
        "upcoming: " + (o["upcoming_event"] or "none"),
    ]
    if o.get("next_review_reason"):
        parts.append("next-step review: " + o["next_review_reason"])
    if o.get("new_activity"):
        parts.append("new activity: " + o["new_activity"])
        evidence = o.get("new_activity_evidence") or {}
        parts.append("activity source: " + str(evidence.get("id")))
        if evidence.get("kind") == "event":
            parts.append("elapsed calendar event; attendance unverified")
    unknown_events = [e for e in o.get("unverified_events", []) if e.get("timing") == "timing_unknown"]
    if unknown_events:
        parts.append(f"event timing unknown: {len(unknown_events)}; verify before reporting")
    if o["open_tasks"]:
        parts.append("open tasks: " + "; ".join(o["open_tasks"]))
    if o.get("duplicate_next_lines"):
        parts.append(f"DUPLICATE Next lines: {o['duplicate_next_lines']}")
    if o.get("task_gap"):
        parts.append("task_gap: no open Task due " + o["next_date"])
    return " | ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("opps")
    ap.add_argument("--tasks")
    ap.add_argument("--events")
    ap.add_argument("--policy", default=str(Path(__file__).resolve().parents[1] / "_shared/policy.json"))
    ap.add_argument("--today")
    ap.add_argument("--as-of", help="Run timestamp with offset; also determines the local date")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    pol = json.loads(Path(a.policy).read_text())
    try:
        as_of = parse_activity_timestamp(a.as_of) if a.as_of else (
            dt.datetime.combine(dt.date.fromisoformat(a.today), dt.time.min, dt.timezone.utc)
            if a.today else dt.datetime.now(dt.timezone.utc)
        )
        today = as_of.date()
        if a.today and dt.date.fromisoformat(a.today) != today:
            ap.error("--today must match the local date in --as-of")
        acts = index_activity(load_records(a.tasks), load_records(a.events), as_of.tzinfo)
    except ValueError as exc:
        ap.error(str(exc))
    results = [check(r, pol, acts, today, as_of) for r in load_records(a.opps)]

    if a.json:
        print(json.dumps(results, indent=1))
        return
    for o in results:
        print(fmt(o))
    scoped = [o for o in results if "blank_fields" in o]
    flagged = [o for o in scoped if o["triggers"]]
    print(
        f"-- {len(results)} open deals as of {today}. In scope: {len(scoped)}. Flagged: {len(flagged)}. "
        + ", ".join(f"{t}: {sum(1 for o in scoped if t in o['triggers'])}" for t in pol["pipeline"]["triggers"])
        + f". Activity sources: tasks {'yes' if a.tasks else 'no'}, events {'yes' if a.events else 'no'}."
    )


if __name__ == "__main__":
    main()
