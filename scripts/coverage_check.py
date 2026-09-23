#!/usr/bin/env python3
"""Check current-run paired source receipts and pagination, not provider authenticity.

See _shared/adapter-contract.md for the normalized, provider-backed receipt format.
Every mode uses the same validation; an issued query alone never counts as coverage.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from email.utils import parseaddr
import json
from pathlib import Path


def stamp(value):
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("receipt timestamps need a timezone offset")
    return value


def quarter_bounds(today):
    start = date(today.year, (today.month - 1) // 3 * 3 + 1, 1)
    def add(months):
        month = start.month - 1 + months
        return date(start.year + month // 12, month % 12 + 1, 1)
    return start, add(3), add(6)


def load_queries(calls, since):
    """Join request/response pairs, then verify whole cursor chains per exact query."""
    groups = defaultdict(list)
    errors = []
    for path in sorted(calls.glob("input_*.json")):
        try:
            request = json.loads(path.read_text())
            started = stamp(request["started_at"])
            if started < since:
                continue
            args = request["arguments"]
            if args["source"] not in ("crm", "mail", "calendar"):
                continue
            output = path.with_name(path.name.replace("input_", "output_", 1))
            response = json.loads(output.read_text())
            result = response["result"]
            if stamp(response["completed_at"]) < started:
                raise ValueError("response predates request")
            if result.get("status") != "success" or result.get("error") or not result.get("provider_reference"):
                raise ValueError("unsuccessful or unreferenced source result")
            if not isinstance(result.get("records"), list):
                raise ValueError("records array missing")
            if not isinstance(result.get("total_count"), int) or result["total_count"] < 0:
                raise ValueError("total_count must be a non-negative integer")
            if not args.get("query_id") or not args.get("provider_query") or not args.get("owner_id"):
                raise ValueError("query_id, owner_id and actual provider_query are required")
            groups[args["query_id"]].append((args, result))
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
    complete = []
    for query_id, pages in groups.items():
        try:
            first = pages[0][0]
            # provider_query may use a page URL/cursor; semantic selection must not change.
            descriptor = {k:v for k,v in first.items() if k not in ("cursor", "provider_query")}
            by_cursor = {}
            total = pages[0][1]["total_count"]
            for args, result in pages:
                if {k:v for k,v in args.items() if k not in ("cursor", "provider_query")} != descriptor:
                    raise ValueError("selection changed across pages")
                cursor = args.get("cursor")
                if cursor in by_cursor:
                    raise ValueError("duplicate request cursor; keep one successful attempt per query/page")
                if result["total_count"] != total:
                    raise ValueError("total changed across pages")
                by_cursor[cursor] = result
            cursor, visited, records = None, set(), []
            while True:
                if cursor in visited or cursor not in by_cursor:
                    raise ValueError("missing page or cursor cycle")
                visited.add(cursor)
                page = by_cursor[cursor]
                records.extend(page["records"])
                cursor = page.get("next_cursor")
                if cursor is None:
                    break
            if len(visited) != len(by_cursor) or len(records) != total:
                raise ValueError("orphan page or total_count mismatch")
            ids = [row.get("Id", row.get("email_id", row.get("event_id"))) for row in records]
            if any(not key for key in ids) or len(set(ids)) != len(ids):
                raise ValueError("missing or duplicate record IDs")
            complete.append({**descriptor, "records": records})
        except (TypeError, ValueError) as exc:
            errors.append(f"{query_id}: {exc}")
    return complete, errors


def check(calls, policy, since, scope):
    queries, errors = load_queries(calls, since)
    owner = policy["identity"].get("owner_id")
    if not owner:
        errors.append("policy.identity.owner_id must identify the CRM owner")
    queries = [q for q in queries if q["owner_id"] == owner]
    pp = policy["pipeline"]
    crm = [q for q in queries if q["source"] == "crm"]
    snapshots = [q for q in crm if q.get("object") == "Opportunity" and q.get("selection") == "all_owned_open"]
    if len(snapshots) != 1:
        errors.append("need exactly one complete all_owned_open Opportunity snapshot")
    opps = snapshots[0]["records"] if len(snapshots) == 1 else []
    if any(o.get("IsClosed") is not False or o.get("OwnerId") != owner for o in opps):
        errors.append("open snapshot contains a closed or differently owned opportunity")
    stages = set(pp["in_scope_stages"])
    current, next_q, end = quarter_bounds(since.date())
    scoped = []
    for opp in opps:
        if opp.get("StageName", "").split(" - ", 1)[0] not in stages:
            continue
        if scope == "forecast":
            try:
                close = date.fromisoformat(opp["CloseDate"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{opp['Id']}: missing/invalid CloseDate; scope unresolved")
                continue
            if not (current <= close < next_q or next_q <= close < end and opp.get("Amount") is not None):
                continue
        scoped.append(opp)
    accounts = {o["AccountId"] for o in scoped}
    opp_ids = {o["Id"] for o in scoped}
    contacts = []
    for obj in ("Contact", "Task", "Event"):
        sources = [q for q in crm if q.get("object") == obj and q.get("selection") == "linked_accounts_and_opportunities"]
        covered = set().union(*(set(q.get("account_ids", [])) for q in sources))
        covered_opps = set().union(*(set(q.get("opportunity_ids", [])) for q in sources))
        if accounts - covered or obj != "Contact" and opp_ids - covered_opps:
            errors.append(f"{obj}: missing Account/Opportunity collection scope")
        if obj == "Contact":
            contacts = [r for q in sources for r in q["records"]]
        if obj == "Event" and any(not {"StartDateTime", "EndDateTime"} <= set(q.get("fields", [])) for q in sources):
            errors.append("Event collection omitted start/end timestamps")
    if scope == "forecast":
        booked = [q for q in crm if q.get("object") == "Opportunity" and q.get("selection") == "booked_in_quarter"
                  and q.get("start_date") == current.isoformat() and q.get("end_date") == next_q.isoformat()]
        if len(booked) != 1:
            errors.append("missing complete booked-in-quarter snapshot")
    internal = set(policy["identity"]["internal_domains"])
    start = since.date() - timedelta(days=1 if scope == "pipeline-daily" else policy["tooling"]["calendar_lookback_days"])
    end_date = since.date() + timedelta(days=policy["tooling"]["calendar_lookahead_days"])
    def covers_dates(q, beginning, ending=None):
        try:
            return date.fromisoformat(q["start_date"]) <= beginning and (ending is None or date.fromisoformat(q["end_date"]) >= ending)
        except (KeyError, TypeError, ValueError):
            return False
    mail = [q for q in queries if q["source"] == "mail"]
    calendar = [q for q in queries if q["source"] == "calendar" and covers_dates(q, start, end_date)]
    inbox = [q for q in mail if q.get("selection") == "external_inbox" and covers_dates(q, start)
             and set(q.get("exclude_domains", [])) == internal
             and not any(q.get(k) for k in ("domains", "account_ids", "query_terms", "extra_filters"))]
    if scope == "pipeline-daily" and not inbox:
        errors.append("missing complete broad weekday inbox search")
    mail_count, cal_count, matched_mail, matched_events = 0, 0, [], []
    for opp in scoped:
        addresses = {c["Email"].lower() for c in contacts if c.get("AccountId") == opp["AccountId"] and c.get("Email")}
        domains = {a.rsplit("@", 1)[-1] for a in addresses} - internal
        if not domains:
            errors.append(f"{opp['Id']}: no external Contact domain")
        mail_start = current if scope == "forecast" else since.date() - timedelta(days=pp["activity_days"])
        searches = inbox if scope == "pipeline-daily" else [q for q in mail if q.get("selection") == "account_inbound"
            and domains <= set(q.get("domains", [])) and covers_dates(q, mail_start)]
        if searches and domains:
            mail_count += 1
        else:
            errors.append(f"{opp['Id']}: incomplete mail coverage")
        events = [q for q in calendar if opp["AccountId"] in q.get("account_ids", [])]
        if events:
            cal_count += 1
        else:
            errors.append(f"{opp['Id']}: incomplete calendar coverage")
        for q in searches:
            for row in q["records"]:
                if parseaddr(row.get("from_", ""))[1].lower().rsplit("@", 1)[-1] in domains:
                    matched_mail.append({"opportunity":opp["Id"], "email_id":row["email_id"], "date":row.get("date"), "subject":row.get("subject")})
        for q in events:
            for row in q["records"]:
                if any(a.get("email", "").lower().rsplit("@", 1)[-1] in domains for a in row.get("attendees", [])):
                    matched_events.append({"opportunity":opp["Id"], "event_id":row["event_id"], "start":row.get("start"), "end":row.get("end")})
    return {"scope":scope, "open_count":len(opps), "in_scope":len(scoped),
        "mail_covered":mail_count, "calendar_covered":cal_count,
        "matched_mail":matched_mail, "matched_calendar":matched_events,
        "ready":not errors, "errors":errors}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calls", required=True, type=Path)
    ap.add_argument("--scope", choices=["pipeline-daily", "pipeline", "forecast"], required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--policy", type=Path, default=Path("_shared/policy.json"))
    args = ap.parse_args()
    result = check(args.calls, json.loads(args.policy.read_text()), stamp(args.since), args.scope)
    print(f"Coverage ({args.scope}): {result['open_count']} open, {result['in_scope']} in scope; mail {result['mail_covered']}/{result['in_scope']}; calendar {result['calendar_covered']}/{result['in_scope']}; {'ready' if result['ready'] else 'INCOMPLETE'}.")
    print(json.dumps(result, indent=2))
    if not result["ready"]:
        print("Resolve gaps or publish an explicitly incomplete report with affected proposals withheld.")
    return int(not result["ready"])


if __name__ == "__main__":
    raise SystemExit(main())
