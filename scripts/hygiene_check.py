#!/usr/bin/env python3
"""Deterministic hygiene check for pipeline-review.

Usage: hygiene_check.py <opps.json> [--tasks tasks.json] [--events events.json]
                        [--policy PATH] [--today YYYY-MM-DD]
                        [--as-of ISO_DATETIME_WITH_OFFSET] [--json]

Inputs are saved CRM query outputs (Opportunity, Task, Event). For every
open deal in policy.pipeline.in_scope_stages it emits one line:
  triggers it can compute from CRM (policy.pipeline.triggers): next_passed,
    new_activity (verified inbound Task or elapsed Event after the newest note),
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
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
    if s is None or s == "":
        return None
    if not isinstance(s, str):
        raise ValueError("date must be an ISO date string")
    return dt.date.fromisoformat(s)


def parse_activity_timestamp(value: str | None) -> dt.datetime | None:
    """Reject timestamps without offsets rather than inventing a timezone."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("activity timestamp must be a string")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Activity timestamp must include a timezone offset")
    return parsed


def classify_event_timing(
    start: dt.datetime | None, end: dt.datetime | None, as_of: dt.datetime
) -> str:
    """A date or invitation alone cannot establish that a meeting has ended."""
    start = start.astimezone(dt.timezone.utc) if start else None
    end = end.astimezone(dt.timezone.utc) if end else None
    as_of = as_of.astimezone(dt.timezone.utc)
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
    return v is None or isinstance(v, str) and not v.strip() or isinstance(v, (list, dict, tuple)) and not v


def validate_next_steps_change(before, after, operation):
    """Check exact plain-text construction, never the truth of a new entry."""
    if before is None:
        before = ""
    if not isinstance(before, str) or not isinstance(after, str):
        return ["NextSteps preimage and proposed value must be plain text"]
    if operation == "unchanged":
        return [] if after == before else ["unchanged NextSteps differs from its preimage"]
    if re.search(r"</?(?:p|br|div|span)\b|&(?:nbsp|amp|lt|gt);", before + after, re.I):
        return ["NextSteps markup needs a separately reviewed normalized conversion"]
    if operation not in ("prepend", "replace_legacy", "insert_history"):
        return ["unsupported NextSteps operation: " + str(operation)]

    def dated_entries(text):
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return False
        for line in lines:
            match = DATED_NEXT_STEP_RE.fullmatch(line)
            if not match:
                return False
            try:
                parse_mdy(match["written"])
            except ValueError:
                return False
        return True

    if operation == "prepend":
        if before and (not after.endswith(before) or len(after) <= len(before)):
            return ["prepend must retain the exact prior NextSteps suffix"]
        inserted = after[:-len(before)] if before else after
        if before and not inserted.endswith(("\n", "\r")):
            return ["new entry must end before the retained first line"]
    else:
        old_lines = before.splitlines(keepends=True)
        if not old_lines:
            return [operation + " requires an existing first entry"]
        first, tail = old_lines[0], "".join(old_lines[1:])
        if operation == "replace_legacy":
            if not NEXT_RE.fullmatch(first.rstrip("\r\n")):
                return ["replace_legacy may remove only a legacy Next: first line"]
            if tail and not after.endswith(tail):
                return ["legacy replacement must retain exact history and line boundaries"]
            inserted = after[:-len(tail)] if tail else after
            if tail and not inserted.endswith(("\n", "\r")):
                return ["replacement must end before retained history"]
        else:
            if not DATED_NEXT_STEP_RE.fullmatch(first.rstrip("\r\n")):
                return ["history insertion requires a dated current first entry"]
            # A formerly unterminated first line needs one separator; its text is unchanged.
            prefix = first if first.endswith(("\n", "\r")) else first + "\n"
            if not after.startswith(prefix) or tail and not after.endswith(tail):
                return ["history insertion must retain the exact first entry and history"]
            end = len(after) - len(tail) if tail else len(after)
            inserted = after[len(prefix):end]
            if tail and not inserted.endswith(("\n", "\r")):
                return ["inserted history must end before retained history"]
    if not dated_entries(inserted):
        return ["inserted NextSteps content must contain valid dated entries"]
    return []


def resolve_as_of(policy, today=None, as_of=None):
    """Use the configured region for dates, including both sides of DST changes."""
    zone = ZoneInfo(policy.get("identity", {}).get("timezone", "UTC"))
    instant = parse_activity_timestamp(as_of) if isinstance(as_of, str) else as_of
    day = dt.date.fromisoformat(today) if isinstance(today, str) else today
    if instant is not None:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("--as-of needs a timezone offset")
        instant = instant.astimezone(zone)
    else:
        instant = dt.datetime.combine(day, dt.time.min, zone) if day else dt.datetime.now(zone)
    if day is not None and day != instant.date():
        raise ValueError("--today must match --as-of in the configured timezone")
    return instant


def validate_policy(pol):
    """Validate only policy consumed by this helper; custom fields stay adapter-owned."""
    try:
        pp = pol["pipeline"]
        order = pp["stage_order"]
        if not isinstance(order, list) or not order or any(not isinstance(s, str) or not s.strip() for s in order) or len(order) != len(set(order)):
            raise ValueError("pipeline.stage_order must contain unique nonblank stage keys")
        scope = pp["in_scope_stages"]
        if not isinstance(scope, list) or any(not isinstance(s, str) or s not in order for s in scope):
            raise ValueError("pipeline.in_scope_stages must name configured stages")
        if pp["close_warning_before_stage"] not in order:
            raise ValueError("pipeline.close_warning_before_stage must name a configured stage")
        for field in ("close_warning_days", "stale_days"):
            if type(pp[field]) is not int or pp[field] < 0:
                raise ValueError("pipeline." + field + " must be a non-negative integer")
        required = pp["required_fields"]
        if not isinstance(required, dict) or any(stage not in order or not isinstance(fields, list) or any(not isinstance(f, str) or not f.strip() for f in fields) for stage, fields in required.items()):
            raise ValueError("pipeline.required_fields must map configured stages to field lists")
        conditions = pp.get("conditional_fields", [])
        if not isinstance(conditions, list) or any(not isinstance(c, dict) or not isinstance(c.get("field"), str) or not c["field"].strip() or not isinstance(c.get("when"), dict) for c in conditions):
            raise ValueError("pipeline.conditional_fields need a field and when object")
        ZoneInfo(pol.get("identity", {}).get("timezone", "UTC"))
    except (KeyError, TypeError, AttributeError, ZoneInfoNotFoundError) as exc:
        raise ValueError("invalid hygiene policy: " + str(exc)) from exc


def check(rec, pol, acts, today, as_of=None, field_types=None):
    pp = pol["pipeline"]
    out = {"Id": rec.get("Id") if isinstance(rec, dict) else None, "Account": "", "Stage": "", "triggers": [], "errors": []}
    if not isinstance(rec, dict):
        out["errors"].append("Opportunity row must be an object")
        return out
    for field in ("Id", "AccountId", "StageName"):
        if not isinstance(rec.get(field), str) or not rec[field].strip():
            out["errors"].append(f"Opportunity {rec.get('Id')}: {field} must be a nonblank string")
    if out["errors"]:
        return out
    stage = rec.get("StageName") or ""
    order = pp["stage_order"]
    stage_key = stage.split(" - ", 1)[0]
    so = order.index(stage_key) if stage_key in order else -1
    account = rec.get("Account")
    if account is not None and (not isinstance(account, dict) or not isinstance(account.get("Name", ""), str)):
        out["errors"].append(f"Opportunity {rec['Id']}: Account must contain a text Name")
        account = None
    acct = (account or {}).get("Name") or rec.get("AccountId") or ""
    next_steps = rec.get("NextSteps")
    if next_steps is not None and not isinstance(next_steps, str):
        out["errors"].append(f"Opportunity {rec['Id']}: NextSteps must be text")
        next_steps = None
    text = clean_text(next_steps)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out.update({"Account": acct, "Stage": stage})
    scope = set(pp["in_scope_stages"])

    if stage_key not in order:
        out["errors"].append(f"Opportunity {rec['Id']}: unknown StageName {stage!r}; scope unresolved")
        return out

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
    types = {"Amount": "number", "NextSteps": "text", "CloseDate": "date"}
    types.update(field_types or {})
    out["unverified_field_types"] = sorted(set(required) - set(types))
    for field in set(required) | {"Amount"}:
        value, kind = rec.get(field), types.get(field)
        if is_blank(value) or kind is None:
            continue
        valid = {"text": isinstance(value, str), "number": type(value) is int or type(value) is float and math.isfinite(value),
                 "boolean": isinstance(value, bool), "array": isinstance(value, list), "object": isinstance(value, dict),
                 "date": isinstance(value, str)}
        if kind not in valid or not valid[kind]:
            out["errors"].append(f"Opportunity {rec['Id']}: {field} must be {kind}")
        elif kind == "date":
            try:
                parse_iso(value)
            except ValueError as exc:
                out["errors"].append(f"Opportunity {rec['Id']}: {field}: {exc}")

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
    # Activity linked to the Opportunity or to its Account. Adapters preserve both activity links.
    items, seen = [], set()
    for a in acts.get(rec.get("Id"), []) + acts.get(rec.get("AccountId"), []):
        k = a.get("id") or (a["date"], a["subject"], a["kind"])
        if k not in seen:
            seen.add(k); items.append(a)
    as_of = as_of or resolve_as_of(pol, today)
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
             or (a["timing"] == "timing_unknown" and a["date"] and a["date"] >= today))
    ]
    open_tasks = [a for a in items if a["kind"] == "open_task"]
    last = max(past, key=lambda a: a["date"]) if past else None
    nxt_ev = None
    out["upcoming_event_order_uncertain"] = False
    if upcoming:
        first_day = min(a["date"] for a in upcoming)
        candidates = [a for a in upcoming if a["date"] == first_day]
        timed = [a for a in candidates if a.get("start")]
        undated = [a for a in candidates if not a.get("start")]
        nxt_ev = min(timed, key=lambda a: (a["start"].astimezone(dt.timezone.utc), a["id"])) if timed else min(undated, key=lambda a: a["id"])
        out["upcoming_event_order_uncertain"] = bool(undated)
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

    try:
        close = parse_iso(rec.get("CloseDate"))
    except ValueError as exc:
        close = None
        out["errors"].append(f"Opportunity {rec['Id']}: CloseDate: {exc}")
    if close and (close < today or (so < order.index(pp["close_warning_before_stage"]) and (close - today).days <= pp["close_warning_days"])):
        out["triggers"].append("date_at_risk")

    cutoff = today - dt.timedelta(days=pp["stale_days"])
    next_live = out.get("next") == "OK" and "next_passed_days" not in out
    if not any(a["date"] >= cutoff for a in past) and not upcoming and not next_live:
        out["triggers"].append("stale")
    activity_errors = [e["message"] for e in getattr(acts, "errors", []) if not e["links"] or set(e["links"]) & {rec["Id"], rec["AccountId"]}]
    out["activity_complete"] = not activity_errors
    if activity_errors:
        out["errors"].extend(activity_errors)
        out["triggers"] = [t for t in out["triggers"] if t not in ("stale", "new_activity")]
        out.pop("new_activity", None)
        out.pop("new_activity_evidence", None)
        out["task_gap"] = None
    return out


class ActivityIndex(defaultdict):
    def __init__(self):
        super().__init__(list)
        self.errors = []


def index_activity(tasks, events, timezone=dt.timezone.utc):
    acts = ActivityIndex()
    for source, rows in (("Task", tasks), ("Event", events)):
        if not isinstance(rows, list):
            acts.errors.append({"links": [], "message": source + " source must be an array"})
            continue
        for index, row in enumerate(rows):
            links = []
            context = f"{source} row {index}"
            try:
                if not isinstance(row, dict):
                    raise ValueError("record must be an object")
                context += " (" + str(row.get("Id")) + ")"
                links = [row[k] for k in ("WhatId", "AccountId") if isinstance(row.get(k), str) and row[k].strip()]
                if not isinstance(row.get("Id"), str) or not row["Id"].strip():
                    raise ValueError("Id must be a nonblank string")
                for field in ("WhatId", "AccountId"):
                    if row.get(field) is not None and (not isinstance(row[field], str) or not row[field].strip()):
                        raise ValueError(field + " must be a nonblank string when supplied")
                if not links:
                    raise ValueError("WhatId or AccountId is required for linkage")
                if row.get("Subject") is not None and not isinstance(row["Subject"], str):
                    raise ValueError("Subject must be text")
                item = {"id": row["Id"], "subject": row.get("Subject") or "", "what_id": row.get("WhatId"), "account_id": row.get("AccountId")}
                def read_date(field, timestamp=False):
                    try:
                        return parse_activity_timestamp(row.get(field)) if timestamp else parse_iso(row.get(field))
                    except ValueError as exc:
                        raise ValueError(field + ": " + str(exc)) from exc
                if source == "Task":
                    if "IsClosed" in row and not isinstance(row["IsClosed"], bool):
                        raise ValueError("IsClosed must be boolean")
                    if row.get("Status") is not None and not isinstance(row["Status"], str):
                        raise ValueError("Status must be text")
                    if "IsClosed" not in row and not row.get("Status"):
                        raise ValueError("IsClosed or Status is required")
                    if row.get("IsClosed") is False and row.get("Status") == "Completed":
                        raise ValueError("IsClosed contradicts completed Status")
                    if row.get("Direction") is not None and row["Direction"] not in ("inbound", "outbound"):
                        raise ValueError("Direction must be inbound or outbound when supplied")
                    who = row.get("Who")
                    if who is not None and (not isinstance(who, dict) or who.get("Name") is not None and not isinstance(who["Name"], str)):
                        raise ValueError("Who must contain a text Name")
                    kind = "open_task" if not row.get("IsClosed", row.get("Status") == "Completed") and row.get("Status") != "Completed" else "inbound" if row.get("Direction") == "inbound" else "task"
                    activity_date = read_date("ActivityDate")
                    if kind != "open_task" and activity_date is None:
                        raise ValueError("ActivityDate is required for a completed Task")
                    item.update(date=activity_date, kind=kind, contact=(who or {}).get("Name"))
                else:
                    start = read_date("StartDateTime", timestamp=True)
                    end = read_date("EndDateTime", timestamp=True)
                    if start and end and end.astimezone(dt.timezone.utc) < start.astimezone(dt.timezone.utc):
                        raise ValueError("EndDateTime precedes StartDateTime")
                    item.update(date=start.astimezone(timezone).date() if start else read_date("ActivityDate"), kind="event", start=start, end=end)
                for link in set(links):
                    acts[link].append(item)
            except (ValueError, TypeError) as exc:
                acts.errors.append({"links": links, "message": context + ": " + str(exc)})
    return acts


def evaluate(opportunities, tasks, events, policy, today=None, as_of=None, field_types=None):
    """Return contextual errors alongside valid diagnostics for local run validation."""
    validate_policy(policy)
    instant = resolve_as_of(policy, today, as_of)
    if not isinstance(opportunities, list):
        raise ValueError("Opportunity source must be an array")
    if field_types is not None and (not isinstance(field_types, dict) or any(kind not in ("text", "number", "boolean", "array", "object", "date") for kind in field_types.values())):
        raise ValueError("adapter field types must name text, number, boolean, array, object or date")
    acts = index_activity(tasks, events, instant.tzinfo)
    known_links = {row.get(key) for row in opportunities if isinstance(row, dict) for key in ("Id", "AccountId") if isinstance(row.get(key), str)}
    for error in acts.errors:
        if not known_links.intersection(error["links"]):
            error["links"] = []
    results = [check(row, policy, acts, instant.date(), instant, field_types) for row in opportunities]
    errors = list(dict.fromkeys([e["message"] for e in acts.errors] + [error for row in results for error in row["errors"]]))
    return {"results": results, "errors": errors, "ready": not errors, "today": instant.date().isoformat(), "as_of": instant.isoformat()}


def fmt(o):
    head = f"{o['Account']} | {o['Stage']} | {o['Id']}"
    if "next" not in o and "next_steps_empty" not in o:
        return head + " | INCOMPLETE: " + "; ".join(o.get("errors", []))
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
    if o.get("upcoming_event_order_uncertain"):
        parts.append("upcoming order uncertain: date-only event may be earlier")
    if o.get("errors"):
        parts.append("INCOMPLETE: " + "; ".join(o["errors"]))
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

    try:
        pol = json.loads(Path(a.policy).read_text())
        outcome = evaluate(load_records(a.opps), load_records(a.tasks), load_records(a.events), pol, a.today, a.as_of)
    except (ValueError, TypeError, OSError) as exc:
        print("Hygiene input error: " + str(exc), file=sys.stderr)
        return 1
    results = outcome["results"]

    if a.json:
        print(json.dumps(results, indent=1))
    else:
        for o in results:
            print(fmt(o))
        scoped = [o for o in results if "blank_fields" in o]
        flagged = [o for o in scoped if o["triggers"]]
        print(f"-- {len(results)} open deals as of {outcome['today']}. In scope: {len(scoped)}. Flagged: {len(flagged)}. "
              + ", ".join(f"{t}: {sum(1 for o in scoped if t in o['triggers'])}" for t in pol["pipeline"].get("triggers", []))
              + f". Activity sources: tasks {'yes' if a.tasks else 'no'}, events {'yes' if a.events else 'no'}.")
    for error in outcome["errors"]:
        print(error, file=sys.stderr)
    return int(not outcome["ready"])


if __name__ == "__main__":
    sys.exit(main())
