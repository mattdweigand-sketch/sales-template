#!/usr/bin/env python3
"""Check current-run paired source receipts and pagination, not provider authenticity.

See _shared/adapter-contract.md for the normalized, provider-backed receipt format.
Every mode uses the same validation; an issued query alone never counts as coverage.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from email.utils import getaddresses
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo


def stamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO string")
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("receipt timestamps need a timezone offset")
    return value


def quarter_bounds(today, forecast=None):
    """Current and next quarter boundaries in the deployment's reporting calendar."""
    forecast = {} if forecast is None else forecast
    if not isinstance(forecast, dict):
        raise ValueError("forecast must be an object")
    boundaries = forecast.get("quarter_boundaries", [])
    if not isinstance(boundaries, list) or any(not isinstance(value, str) for value in boundaries):
        raise ValueError("quarter_boundaries must be a list of ISO dates")
    if boundaries:
        days = [date.fromisoformat(value) for value in boundaries]
        if days != sorted(set(days)):
            raise ValueError("quarter_boundaries must be unique, ascending ISO dates")
        for index in range(len(days) - 2):
            if days[index] <= today < days[index + 1]:
                return tuple(days[index:index + 3])
        raise ValueError("quarter_boundaries must cover the current and next quarter")
    first_month = forecast.get("fiscal_year_start_month", 1)
    if type(first_month) is not int or not 1 <= first_month <= 12:
        raise ValueError("fiscal_year_start_month must be an integer from 1 to 12")
    month_index = today.year * 12 + today.month - 1
    start_index = month_index - (today.month - first_month) % 3
    start = date(start_index // 12, start_index % 12 + 1, 1)
    def add(months):
        month = start.month - 1 + months
        return date(start.year + month // 12, month % 12 + 1, 1)
    return start, add(3), add(6)


def reference_path(calls, value):
    """References are relative to calls; siblings inside the run are permitted."""
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        raise ValueError("evidence reference must be a nonempty relative path")
    root = Path(os.path.abspath(Path(calls).parent))
    target = Path(os.path.abspath(Path(calls) / value))
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("evidence reference escapes the run") from None
    for part in (target, *target.parents):
        if part.is_symlink():
            raise ValueError("evidence reference has a symlink")
        if part == root:
            break
    if not target.is_file():
        raise ValueError("evidence reference is not a saved file: " + value)
    return target


def address(value):
    if not isinstance(value, str):
        raise ValueError("address must be a string")
    parsed = getaddresses([value])
    if len(parsed) != 1:
        raise ValueError("address must identify one sender/recipient")
    email = parsed[0][1].lower()
    if email.count("@") != 1 or any(c.isspace() for c in email) or not all(email.split("@")):
        raise ValueError("invalid email address")
    return email


def validate_mail_row(row):
    if not isinstance(row, dict):
        raise ValueError("record must be an object")
    for field in ("email_id", "thread_id", "date", "from_"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError("missing/invalid " + field)
    stamp(row["date"])
    address(row["from_"])
    for field in ("to", "cc"):
        if field in row:
            if not isinstance(row[field], list):
                raise ValueError(field + " must be an address list")
            for value in row[field]:
                address(value)
    for field in ("subject", "body", "body_text", "snippet"):
        if row.get(field) is not None and not isinstance(row[field], str):
            raise ValueError(field + " must be text")
    if row.get("attachments") is not None:
        if not isinstance(row["attachments"], list) or any(
            not isinstance(a, dict) or not isinstance(a.get("filename"), str) for a in row["attachments"]
        ):
            raise ValueError("attachments must contain filename objects")


def load_queries(calls, since):
    """Join saved pairs and validate exact complete cursor chains, not authenticity."""
    calls = Path(calls)
    groups, errors = defaultdict(list), []
    if since.tzinfo is None or since.utcoffset() is None:
        return [], ["run start must include a timezone offset"]
    if not calls.is_dir() or calls.is_symlink():
        return [], ["calls must be a real saved directory"]
    for path in sorted(calls.glob("input_*.json")):
        label = path.name
        try:
            if path.is_symlink():
                raise ValueError("request is a symlink")
            request = json.loads(path.read_text())
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            started = stamp(request.get("started_at"))
            if started < since:
                continue
            args = request.get("arguments")
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            if {"records", "provider_references", "receipt_files"} & set(args):
                raise ValueError("arguments contain reserved checker output fields")
            label += " query=" + str(args.get("query_id", "unknown"))
            if args.get("source") not in ("crm", "mail", "calendar"):
                raise ValueError("unsupported source")
            for key in ("query_id", "provider_query", "owner_id", "selection"):
                if not isinstance(args.get(key), str) or not args[key].strip():
                    raise ValueError(key + " must be a nonempty string")
            if "cursor" not in args or args["cursor"] is not None and not isinstance(args["cursor"], str):
                raise ValueError("cursor must be explicit null or a string")
            output = path.with_name(path.name.replace("input_", "output_", 1))
            if output.is_symlink():
                raise ValueError("response is a symlink")
            response = json.loads(output.read_text())
            if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
                raise ValueError("response/result must be objects")
            result = response["result"]
            if stamp(response.get("completed_at")) < started:
                raise ValueError("response predates request")
            if result.get("status") != "success" or result.get("error") or result.get("authenticated") is False:
                raise ValueError("unsuccessful source result")
            reference_path(calls, result.get("provider_reference"))
            if not isinstance(result.get("records"), list):
                raise ValueError("records array missing")
            if type(result.get("total_count")) is not int or result["total_count"] < 0:
                raise ValueError("total_count must be a non-negative integer")
            if "next_cursor" not in result or result["next_cursor"] is not None and not isinstance(result["next_cursor"], str):
                raise ValueError("next_cursor must be explicit null or a string")
            for index, row in enumerate(result["records"]):
                try:
                    if not isinstance(row, dict):
                        raise ValueError("record must be an object")
                    key = {"crm":"Id", "mail":"email_id", "calendar":"event_id"}[args["source"]]
                    if not isinstance(row.get(key), str) or not row[key].strip():
                        raise ValueError("missing/invalid " + key)
                    if args["source"] == "mail":
                        validate_mail_row(row)
                    if args["source"] == "crm":
                        for key in ("AccountId", "WhatId"):
                            if key in row and row[key] is not None and (not isinstance(row[key], str) or not row[key].strip()):
                                raise ValueError("invalid " + key)
                        if row.get("Email") is not None:
                            address(row["Email"])
                        if row.get("Amount") is not None and (type(row["Amount"]) not in (int, float) or type(row["Amount"]) is float and not math.isfinite(row["Amount"])):
                            raise ValueError("Amount must be a finite number or null")
                    if args["source"] == "calendar":
                        if not isinstance(row.get("attendees", []), list):
                            raise ValueError("attendees must be a list")
                        for attendee in row.get("attendees", []):
                            if not isinstance(attendee, dict):
                                raise ValueError("attendee must be an object")
                            address(attendee.get("email"))
                        for key in ("start", "end"):
                            if row.get(key) is not None:
                                stamp(row[key])
                except (ValueError, TypeError) as exc:
                    raise ValueError("record=" + str(row.get("Id", row.get("email_id", row.get("event_id", index))) if isinstance(row, dict) else index) + ": " + str(exc)) from None
            groups[args["query_id"]].append((args, result, path.name, output.name))
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(f"{label}: {exc}")
    complete = []
    for query_id, pages in groups.items():
        try:
            descriptor = {k:v for k,v in pages[0][0].items() if k not in ("cursor", "provider_query")}
            by_cursor, total = {}, pages[0][1]["total_count"]
            for args, result, _, _ in pages:
                if {k:v for k,v in args.items() if k not in ("cursor", "provider_query")} != descriptor:
                    raise ValueError("selection changed across pages")
                cursor = args["cursor"]
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
                cursor = page["next_cursor"]
                if cursor is None:
                    break
            if len(visited) != len(by_cursor) or len(records) != total:
                raise ValueError("orphan page or total_count mismatch")
            key = {"crm":"Id", "mail":"email_id", "calendar":"event_id"}[descriptor["source"]]
            ids = [row[key] for row in records]
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate record IDs")
            complete.append({**descriptor, "records": records,
                "provider_references": [p[1]["provider_reference"] for p in pages],
                "receipt_files": [name for p in pages for name in p[2:]]})
        except (TypeError, ValueError) as exc:
            errors.append(f"{query_id}: {exc}")
    return complete, errors


# Permitted semantic descriptors; projection and pagination do not narrow scope.
COMMON_ARGUMENTS = {"query_id", "source", "owner_id", "selection", "object", "fields", "page_size", "records", "provider_references", "receipt_files"}
SELECTION_ARGUMENTS = {
    "all_owned_open": set(),
    "linked_accounts_and_opportunities": {"account_ids", "opportunity_ids"},
    "booked_in_quarter": {"start_date", "end_date"},
    "selected_tasks": {"task_ids"},
    "external_inbox": {"start_date", "end_date", "exclude_domains"},
    "account_inbound": {"start_date", "end_date", "domains"},
    "account_calendar": {"start_date", "end_date", "account_ids", "addresses"},
    "contact_history": {"start_date", "end_date", "addresses", "direction"},
}


def selection_error(query):
    allowed = SELECTION_ARGUMENTS.get(query.get("selection"))
    if allowed is None:
        return "unsupported selection"
    extra = set(query) - COMMON_ARGUMENTS - allowed
    if extra:
        return "unsupported narrowing/arguments: " + ", ".join(sorted(extra))
    for key in ("domains", "exclude_domains", "account_ids", "opportunity_ids", "task_ids", "addresses", "fields"):
        if key in query and (not isinstance(query[key], list) or any(not isinstance(x, str) or not x.strip() for x in query[key])):
            return key + " must be a list of nonempty strings"
    try:
        for value in query.get("addresses", []):
            address(value)
    except ValueError as exc:
        return "addresses: " + str(exc)
    return None


def covers_dates(query, beginning, ending, allow_open=False):
    try:
        start = date.fromisoformat(query["start_date"])
        end = query["end_date"]
        if end is None:
            return allow_open and start <= beginning
        end = date.fromisoformat(end)
        return start < end and start <= beginning and end >= ending
    except (KeyError, TypeError, ValueError):
        return False


def check(calls, policy, since, scope):
    queries, errors = load_queries(calls, since)
    output = {"scope":scope, "open_count":0, "in_scope":0, "in_scope_ids":[], "booked_ids":[],
        "unresolved_scope":[], "mail_covered":0, "calendar_covered":0,
        "matched_mail":[], "matched_calendar":[], "ready":False, "errors":errors}
    try:
        owner = policy["identity"]["owner_id"]
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("identity.owner_id must identify the CRM owner")
        run_day = since.astimezone(ZoneInfo(policy["identity"]["timezone"])).date()
        pp, tooling = policy["pipeline"], policy["tooling"]
        order, stages = pp["stage_order"], pp["in_scope_stages"]
        for key, values in (("stage_order", order), ("in_scope_stages", stages)):
            if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values) or len(set(values)) != len(values):
                raise ValueError(key + " must contain unique nonempty stage keys")
        if not set(stages) <= set(order) or pp["close_warning_before_stage"] not in order:
            raise ValueError("scope/warning stages must belong to stage_order")
        for section, key in ((pp,"activity_days"),(tooling,"calendar_lookback_days"),(tooling,"calendar_lookahead_days")):
            if type(section[key]) is not int or section[key] < 0:
                raise ValueError(key + " must be a non-negative integer")
        raw_internal = policy["identity"]["internal_domains"]
        if not isinstance(raw_internal, list) or any(not isinstance(d, str) or not d.strip() for d in raw_internal):
            raise ValueError("internal_domains must be a list of domains")
        internal = {d.lower() for d in raw_internal}
        current, next_q, end = quarter_bounds(run_day, policy.get("forecast") if scope == "forecast" else None)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append("policy: " + str(exc))
        return output
    queries = [q for q in queries if q["owner_id"] == owner]
    crm = []
    for query in queries:
        if query["source"] == "crm":
            problem = selection_error(query)
            if problem:
                errors.append(query["query_id"] + ": " + problem)
            else:
                crm.append(query)
    snapshots = [q for q in crm if q.get("object") == "Opportunity" and q.get("selection") == "all_owned_open"]
    if len(snapshots) != 1:
        errors.append("need exactly one complete all_owned_open Opportunity snapshot")
    opps = snapshots[0]["records"] if len(snapshots) == 1 else []
    output["open_count"] = len(opps)
    scoped = []
    for opp in opps:
        oid = opp["Id"]
        if opp.get("IsClosed") is not False or opp.get("OwnerId") != owner:
            errors.append(oid + ": open snapshot contains a closed or differently owned opportunity")
        stage = opp.get("StageName")
        if not isinstance(stage, str) or stage.split(" - ", 1)[0] not in order:
            errors.append(oid + ": missing/invalid/unmapped StageName; scope unresolved")
            output["unresolved_scope"].append(oid)
            continue
        if stage.split(" - ", 1)[0] not in stages:
            continue
        if not isinstance(opp.get("AccountId"), str) or not opp["AccountId"].strip():
            errors.append(oid + ": missing/invalid AccountId; scope unresolved")
            output["unresolved_scope"].append(oid)
            continue
        if scope == "forecast":
            try:
                if "Amount" not in opp:
                    raise ValueError("Amount was not collected")
                close = date.fromisoformat(opp["CloseDate"])
            except (KeyError, TypeError, ValueError):
                errors.append(oid + ": missing/invalid CloseDate or uncollected Amount; scope unresolved")
                output["unresolved_scope"].append(oid)
                continue
            if not (current <= close < next_q or next_q <= close < end and opp.get("Amount") is not None):
                continue
        scoped.append(opp)
    output["in_scope"] = len(scoped)
    output["in_scope_ids"] = [o["Id"] for o in scoped]
    accounts, opp_ids = {o["AccountId"] for o in scoped}, set(output["in_scope_ids"])
    contacts = []
    for obj in ("Contact", "Task", "Event"):
        sources = [q for q in crm if q.get("object") == obj and q.get("selection") == "linked_accounts_and_opportunities"]
        covered, covered_opps = set(), set()
        for query in sources:
            for key, target in (("account_ids",covered),("opportunity_ids",covered_opps)):
                values = query.get(key)
                if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                    errors.append(query["query_id"] + ": invalid " + key)
                else:
                    target.update(values)
            if obj == "Contact":
                contacts.extend(query["records"])
            fields = query.get("fields")
            if obj == "Event" and (not isinstance(fields, list) or any(not isinstance(v, str) for v in fields) or not {"StartDateTime", "EndDateTime"} <= set(fields)):
                errors.append("Event collection omitted start/end timestamps")
        if accounts - covered or obj != "Contact" and opp_ids - covered_opps:
            errors.append(f"{obj}: missing Account/Opportunity collection scope")
    if scope == "forecast":
        booked = [q for q in crm if q.get("object") == "Opportunity" and q.get("selection") == "booked_in_quarter"
                  and q.get("start_date") == current.isoformat() and q.get("end_date") == next_q.isoformat()]
        if len(booked) != 1:
            errors.append("missing complete booked-in-quarter snapshot")
        else:
            for row in booked[0]["records"]:
                output["booked_ids"].append(row["Id"])
                try:
                    if row.get("OwnerId") != owner or row.get("IsClosed") is not True or row.get("IsWon") is not True or not current <= date.fromisoformat(row["CloseDate"]) < next_q:
                        raise ValueError("row is not an owned won deal in this quarter")
                except (KeyError, TypeError, ValueError) as exc:
                    errors.append(row["Id"] + ": booked snapshot: " + str(exc))
            if set(output["booked_ids"]) & {row["Id"] for row in opps}:
                errors.append("booked and open snapshots contain overlapping opportunity IDs")
    valid_sources = []
    for query in queries:
        if query["source"] in ("mail", "calendar"):
            problem = selection_error(query)
            if problem:
                errors.append(query["query_id"] + ": " + problem)
            else:
                valid_sources.append(query)
    start = run_day - timedelta(days=1 if scope == "pipeline-daily" else tooling["calendar_lookback_days"])
    calendar_end = run_day + timedelta(days=tooling["calendar_lookahead_days"] + 1)
    mail_end = run_day + timedelta(days=1)
    mail = [q for q in valid_sources if q["source"] == "mail"]
    calendar = [q for q in valid_sources if q["source"] == "calendar" and q["selection"] == "account_calendar" and covers_dates(q,start,calendar_end)]
    inbox = [q for q in mail if q["selection"] == "external_inbox" and covers_dates(q,start,mail_end,True)
             and {d.lower() for d in q.get("exclude_domains", [])} == internal]
    if scope == "pipeline-daily" and not inbox:
        errors.append("missing complete broad weekday inbox search")
    for opp in scoped:
        addresses = {c["Email"].lower() for c in contacts if c.get("AccountId") == opp["AccountId"] and c.get("Email")}
        domains = {address(a).rsplit("@", 1)[-1] for a in addresses} - internal
        if not domains:
            errors.append(f"{opp['Id']}: no external Contact domain")
        mail_start = current if scope == "forecast" else run_day - timedelta(days=pp["activity_days"])
        searches = inbox if scope == "pipeline-daily" else [q for q in mail if q["selection"] == "account_inbound"
            and domains <= {d.lower() for d in q.get("domains", [])} and covers_dates(q,mail_start,mail_end,True)]
        if searches and domains:
            output["mail_covered"] += 1
        else:
            errors.append(f"{opp['Id']}: incomplete mail coverage")
        contact_addresses = {address(a) for a in addresses}
        events = [q for q in calendar if opp["AccountId"] in q.get("account_ids", [])
                  and ("addresses" not in q or contact_addresses <= {address(a) for a in q["addresses"]})]
        if events:
            output["calendar_covered"] += 1
        else:
            errors.append(f"{opp['Id']}: incomplete calendar coverage")
        for query in searches:
            for row in query["records"]:
                if address(row["from_"]).rsplit("@", 1)[-1] in domains:
                    output["matched_mail"].append({"opportunity":opp["Id"], "email_id":row["email_id"], "date":row.get("date"), "subject":row.get("subject")})
        for query in events:
            for row in query["records"]:
                if any(address(a["email"]).rsplit("@", 1)[-1] in domains for a in row.get("attendees", [])):
                    output["matched_calendar"].append({"opportunity":opp["Id"], "event_id":row["event_id"], "start":row.get("start"), "end":row.get("end")})
    output["ready"] = not errors
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calls", required=True, type=Path)
    ap.add_argument("--scope", choices=["pipeline-daily", "pipeline", "forecast"], required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--policy", type=Path, default=Path("_shared/policy.json"))
    args = ap.parse_args()
    try:
        result = check(args.calls, json.loads(args.policy.read_text()), stamp(args.since), args.scope)
    except (TypeError, ValueError, OSError) as exc:
        print(json.dumps({"scope":args.scope,"ready":False,"errors":[str(exc)]}, indent=2))
        return 1
    print(f"Coverage ({args.scope}): {result['open_count']} open, {result['in_scope']} in scope; mail {result['mail_covered']}/{result['in_scope']}; calendar {result['calendar_covered']}/{result['in_scope']}; {'ready' if result['ready'] else 'INCOMPLETE'}.")
    print(json.dumps(result, indent=2))
    if not result["ready"]:
        print("Resolve gaps or publish an explicitly incomplete report with affected proposals withheld.")
    return int(not result["ready"])


if __name__ == "__main__":
    raise SystemExit(main())
