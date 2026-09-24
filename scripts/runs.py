#!/usr/bin/env python3
"""Copy a run starter and inspect its review state. Never calls an external service."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from zoneinfo import ZoneInfo

from wrappers import ROOT, load_routes, safe_path

RUN_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")

# These are the five supported workflows, not a configurable execution engine.
REQUIRED = {
    "sales-call-prep": {"selected_call"},
    "interaction-sync": {"interaction", "reconciliation"},
    "task-triage-speed-run": {"tasks", "triage", "calls", "mail"},
    "pipeline-review": {"opportunities", "tasks", "events", "calls"},
    "forecast-weekly": {"opportunities", "tasks", "events", "calls", "forecast"},
}


def inside(path, ref, directory=False):
    if not isinstance(ref, str) or not ref or Path(ref).is_absolute() or ".." in Path(ref).parts:
        raise ValueError("source must be a path inside this run: " + str(ref))
    target = path / ref
    if any(p.is_symlink() for p in [target] + list(target.parents)[:len(Path(ref).parts)]):
        raise ValueError("source path must not contain symlinks: " + ref)
    if not target.exists() or not directory and not target.is_file():
        raise ValueError("missing source: " + ref)
    return target


def read_json(path):
    return json.loads(regular(path).read_text())


def same_json(left, right):
    # Python container equality conflates False/0 and True/1.
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def atomic_json(path, doc):
    regular(path)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink():
        raise ValueError("temporary result path must not be a symlink")
    temporary.write_text(json.dumps(doc, indent=2) + "\n")
    temporary.replace(path)


def binding(path, name):
    doc = read_json(path / "inputs.json")
    if not isinstance(doc, dict) or set(doc) - {"started_at", "mode", "sources", "unavailable_sources", "effects"}:
        raise ValueError("inputs.json has unsupported fields or is not an object")
    from coverage_check import stamp
    stamp(doc["started_at"])
    if name == "pipeline-review" and doc.get("mode") not in ("daily", "extended"):
        raise ValueError("pipeline mode must be daily or extended")
    sources = doc.get("sources")
    allowed = REQUIRED[name] | {"calls", "mail"}
    if not isinstance(sources, dict) or set(sources) - allowed:
        raise ValueError("unknown source names for " + name)
    gaps = doc.get("unavailable_sources")
    if not isinstance(gaps, list) or any(not isinstance(g, dict) or set(g) != {"name", "reason"}
            or g["name"] not in allowed or not isinstance(g["reason"], str) or not g["reason"].strip() for g in gaps):
        raise ValueError("unavailable_sources needs named sources and concrete reasons")
    if len({g["name"] for g in gaps}) != len(gaps) or set(sources) & {g["name"] for g in gaps}:
        raise ValueError("duplicate or conflicting source declarations")
    for ref in sources.values():
        inside(path, ref, directory=True)
    if not isinstance(doc.get("effects"), list):
        raise ValueError("effects must be a list")
    return doc


def source_files(path, doc):
    """Freeze bound directories and every nested evidence reference, once."""
    files = {path / "inputs.json"}
    opaque = set()
    pending = [inside(path, ref, directory=True) for ref in doc["sources"].values()]
    # Effect evidence is part of the proposal; later apply receipts are separate.
    for effect in doc["effects"]:
        if isinstance(effect, dict):
            pending += [inside(path, ref) for ref in effect.get("source_refs", [])]
    def references(value, base):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("source_refs", "evidence_refs", "provider_reference"):
                    refs = [item] if isinstance(item, str) else item
                    if not isinstance(refs, list):
                        raise ValueError("invalid evidence reference list")
                    for ref in refs:
                        if not isinstance(ref, str) or not ref or Path(ref).is_absolute() or base == path and ".." in Path(ref).parts:
                            raise ValueError("evidence references must be paths")
                        # Receipt-native references are relative to calls; all other refs to run.
                        target = base / ref
                        resolved = target.resolve()
                        if not resolved.is_relative_to(path.resolve()):
                            raise ValueError("evidence reference escapes run")
                        # Permit ../raw from calls only, but never symlink traversal.
                        for ancestor in [target] + list(target.parents):
                            if ancestor == path:
                                break
                            if ancestor.is_symlink():
                                raise ValueError("symlinked evidence reference")
                        target = regular(Path(os.path.normpath(target)))
                        pending.append(target)
                        if key == "provider_reference":
                            opaque.add(target)
                else:
                    references(item, base)
        elif isinstance(value, list):
            for item in value:
                references(item, base)
    calls = path / doc["sources"].get("calls", "__no_calls__")
    mail = path / doc["sources"].get("mail", "__no_mail__")
    while pending:
        target = pending.pop()
        if target in files:
            continue
        if target.is_symlink():
            raise ValueError("bound directories must not contain symlinks")
        if target.is_dir():
            pending.extend(target.iterdir())
            continue
        regular(target)
        if target.name in ("review.json", "02_result.json") or "effect-evidence" in target.relative_to(path).parts:
            raise ValueError("mutable apply receipts cannot be collection inputs")
        files.add(target)
        if target.suffix == ".json" and target not in opaque and target != mail and not target.is_relative_to(mail):
            references(read_json(target), calls if target.parent == calls else path)
    return files


def rows(path):
    value = read_json(path)
    if isinstance(value, dict):
        value = value.get("result", value)
        if isinstance(value, dict):
            value = value.get("records")
    if not isinstance(value, list) or any(not isinstance(r, dict) or not isinstance(r.get("Id"), str) or not r["Id"] for r in value):
        raise ValueError(path.name + ": expected records with stable Id")
    if len({r["Id"] for r in value}) != len(value):
        raise ValueError(path.name + ": duplicate record IDs")
    return value


def configuration_errors(name, policy):
    """Only settings actually used by the selected procedure/report."""
    errors = []
    try:
        if name in ("pipeline-review", "forecast-weekly"):
            precision = policy["reporting"]["amount_decimal_places"]
            if type(precision) is not int or precision < 0:
                errors.append("reporting.amount_decimal_places must be a nonnegative integer")
            for key in ("week_start_weekday", "extended_review_weekday"):
                value = policy["cadence"][key]
                if type(value) is not int or not 0 <= value <= 6:
                    errors.append("cadence." + key + " must be an integer from 0 to 6")
        if name == "forecast-weekly":
            forecast = policy["forecast"]
            sources = forecast["sources"]
            if not isinstance(sources, list) or any(not isinstance(v, str) for v in sources) or sorted(sources) != ["calendar", "crm", "mail"]:
                errors.append("forecast.sources must contain crm, calendar and mail exactly once")
            stages = forecast["commit_stages"]
            if not isinstance(stages, list) or any(s not in policy["pipeline"]["in_scope_stages"] for s in stages):
                errors.append("forecast.commit_stages must use configured in-scope stages")
            for key in ("activity_days", "next_quarter_preview_days"):
                if type(forecast[key]) is not int or forecast[key] < 0:
                    errors.append("forecast." + key + " must be a nonnegative integer")
            if any(not isinstance(forecast["category_mapping"].get(key), str) or not forecast["category_mapping"][key].strip() for key in ("commit", "upside")):
                errors.append("forecast.category_mapping needs Commit/Upside labels")
            targets = forecast["targets"]
            if not isinstance(targets, dict):
                errors.append("forecast.targets must be a quarter-start map")
            else:
                from datetime import date
                from decimal import Decimal
                for key in targets:
                    date.fromisoformat(key)
                for value in [forecast.get("target_default")] + list(targets.values()):
                    if value is not None and (isinstance(value, bool) or not Decimal(str(value)).is_finite() or Decimal(str(value)) < 0):
                        errors.append("forecast targets must be finite nonnegative amounts or null")
    except (KeyError, TypeError, ValueError, AttributeError, ArithmeticError) as exc:
        errors.append("selected workflow configuration: " + str(exc))
    return errors


def check_effects(path, name, doc, proposed, policy=None):
    from hygiene_check import validate_next_steps_change
    from coverage_check import address
    from datetime import date
    import math
    policy = policy or read_json(path.parents[1] / "_shared/policy.json")
    errors, ids = [], []
    allowed = {
        "interaction-sync": {"Opportunity": {"Amount", "CloseDate", "StageName", "NextSteps", "Description"}, "Contact": {"Email", "Title", "AccountId", "Description"}, "Task": {"ActivityDate", "Status", "Description"}},
        "task-triage-speed-run": {"Task": {"ActivityDate", "Status", "Subject", "Description", "WhoId"}, "Contact": {"Email", "Title", "AccountId", "Description"}},
        "pipeline-review": {"Opportunity": {"StageName", "CloseDate", "NextSteps", "Amount", "Description"}},
        "forecast-weekly": {"Opportunity": {"CloseDate", "NextSteps", "ForecastCategoryName"}, "Contact": {"Email"}},
        "sales-call-prep": {},
    }[name]
    creates = {}
    if name in ("interaction-sync", "task-triage-speed-run"):
        creates["Contact"] = {"FirstName", "LastName", "Email", "Title", "AccountId", "OwnerId"}
    if name in ("interaction-sync", "pipeline-review"):
        creates["Task"] = {"ActivityDate", "Status", "Subject", "Description", "TaskSubtype", "WhoId", "WhatId", "OwnerId"}
    if name == "interaction-sync":
        creates["OpportunityContactRole"] = {"OpportunityId", "ContactId", "Role", "IsPrimary"}
    if name in ("interaction-sync", "pipeline-review"):
        for fields in policy.get("pipeline", {}).get("required_fields", {}).values():
            allowed["Opportunity"].update(fields)
        for conditional in policy.get("pipeline", {}).get("conditional_fields", []):
            allowed["Opportunity"].add(conditional["field"])
        allowed["Opportunity"] -= {"Id", "OwnerId", "IsWon", "IsClosed"}
    for effect in doc["effects"]:
        try:
            if not isinstance(effect, dict) or set(effect) - {"id", "operation", "destination", "record_id", "preimage", "payload", "source_refs", "absent_fields", "history_operation"}:
                raise ValueError("unsupported effect fields")
            if {"id", "operation", "destination", "record_id", "preimage", "payload", "source_refs"} - set(effect):
                raise ValueError("missing required effect fields")
            eid = effect["id"]
            if not isinstance(eid, str) or not re.fullmatch(r"[a-zA-Z0-9-]+", eid):
                raise ValueError("invalid effect ID")
            ids.append(eid)
            op, dest, payload, before = (effect[k] for k in ("operation", "destination", "payload", "preimage"))
            if not isinstance(before, dict) or not isinstance(payload, dict) or not payload:
                raise ValueError("exact nonempty payload and preimage object required")
            refs = effect["source_refs"]
            if not isinstance(refs, list) or not refs:
                raise ValueError("effect requires source_refs")
            for ref in refs:
                inside(path, ref)
            if op == "local_config":
                if not isinstance(dest, str) or not dest.startswith("_shared/") or set(payload) != {"staged_file"}:
                    raise ValueError("local_config needs a shared destination and staged_file payload")
                staged = inside(path, payload["staged_file"])
                digest = hashlib.sha256(staged.read_bytes()).hexdigest()
                if review_metadata(path).get("expected_after", {}).get(eid) != {dest: digest} or payload["staged_file"] not in refs:
                    raise ValueError("local configuration must bind exact staged bytes and expected_after")
                continue
            if name == "sales-call-prep":
                raise ValueError("Call Prep permits no external effects")
            if op == "draft":
                if name not in ("interaction-sync", "task-triage-speed-run") or dest != "mail" or effect.get("record_id") is not None:
                    raise ValueError("draft operation not allowed here")
                if set(payload) != {"to", "cc", "bcc", "subject", "body", "attachments", "thread_id", "reply_to_message_id"}:
                    raise ValueError("draft requires exact recipients, text, attachments and reply identity")
                if not all(isinstance(payload[k], list) for k in ("to", "cc", "bcc", "attachments")) or not payload["to"]:
                    raise ValueError("draft recipient/attachment lists are invalid")
                for key in ("to", "cc", "bcc"):
                    for value in payload[key]:
                        address(value)
                for key in ("thread_id", "reply_to_message_id"):
                    if payload[key] is not None and (not isinstance(payload[key], str) or not payload[key].strip()):
                        raise ValueError(key + " must be a nonblank string or null")
                for ref in payload["attachments"]:
                    inside(path, ref)
                    if ref not in refs:
                        raise ValueError("draft attachment must be a bound source_ref")
                if not all(isinstance(payload[k], str) and payload[k].strip() for k in ("subject", "body")):
                    raise ValueError("draft subject and body are required")
                if "existing_draft_ids" not in before or before["existing_draft_ids"] != []:
                    raise ValueError("draft preimage must establish no existing matching draft")
            elif op in ("update", "create"):
                fields = creates if op == "create" else allowed
                if dest not in fields or set(payload) - fields[dest]:
                    raise ValueError("destination or fields forbidden for selected workflow")
                for field, value in payload.items():
                    if field == "Amount" and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                        raise ValueError("Amount must be a finite nonnegative number; negative adjustments need separate review")
                    if field in ("ActivityDate", "CloseDate"):
                        date.fromisoformat(value)
                    if field == "Email":
                        address(value)
                    if field in {"StageName", "Status", "Subject", "Description", "NextSteps", "Title", "FirstName", "LastName", "AccountId", "OwnerId", "WhoId", "WhatId", "ContactId", "OpportunityId", "Role", "TaskSubtype", "ForecastCategoryName"} and not isinstance(value, str):
                        raise ValueError(field + " must be text")
                    if field == "IsPrimary" and type(value) is not bool:
                        raise ValueError("IsPrimary must be boolean")
                if op == "create" and (dest == "Opportunity" or effect.get("record_id") is not None or name == "forecast-weekly"):
                    raise ValueError("create cannot invent an ID or create this record type")
                if op == "update":
                    if not isinstance(effect.get("record_id"), str) or not effect["record_id"].strip():
                        raise ValueError("update requires record_id")
                    absent = effect.get("absent_fields", [])
                    if not isinstance(absent, list) or any(not isinstance(v, str) for v in absent) or set(absent) & set(before):
                        raise ValueError("absent_fields must distinguish absent fields from null preimages")
                    if set(payload) - set(before) - set(absent):
                        raise ValueError("every changed field needs an exact preimage or explicit absence")
                if "NextSteps" in payload:
                    errors += [eid + ": " + e for e in validate_next_steps_change(before.get("NextSteps"), payload["NextSteps"], effect.get("history_operation"))]
                if "Description" in payload and before.get("Description"):
                    if not isinstance(payload["Description"], str) or not payload["Description"].endswith(before["Description"]):
                        raise ValueError("Description prepend must retain exact prior suffix")
            else:
                raise ValueError("unsupported operation (send/delete/merge are forbidden)")
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(str(effect.get("id", "effect") if isinstance(effect, dict) else "effect") + ": " + str(exc))
    if len(ids) != len(set(ids)) or set(ids) != set(proposed):
        errors.append("inputs effects must match unique Effect headings exactly")
    return errors


def check_readback(path, effect, result, reviewed_at):
    """Compare local apply receipts to the frozen proposal; not provider authentication."""
    if effect["operation"] == "local_config":
        return
    from coverage_check import stamp
    evidence = {}
    for key in ("preimage_reference", "provider_reference", "readback_reference"):
        ref = result.get(key)
        if not isinstance(ref, str) or not ref.startswith("effect-evidence/"):
            raise ValueError("verified external effect needs " + key + " under effect-evidence/")
        evidence[key] = read_json(inside(path, ref))
        if evidence[key].get("effect_id") != effect["id"]:
            raise ValueError("effect evidence has wrong effect_id")
    pre = evidence["preimage_reference"]
    provider = evidence["provider_reference"]
    after = evidence["readback_reference"]
    if stamp(pre["observed_at"]) < stamp(reviewed_at) or stamp(after["observed_at"]) < stamp(pre["observed_at"]):
        raise ValueError("apply preimage/readback must follow review in order")
    if pre.get("record_id") != effect.get("record_id") or not same_json(pre.get("fields"), effect["preimage"]) or set(pre.get("absent_fields", [])) != set(effect.get("absent_fields", [])):
        raise ValueError("fresh preimage differs from frozen proposal")
    if provider.get("operation") != effect["operation"] or provider.get("destination") != effect["destination"] or not same_json(provider.get("payload"), effect["payload"]):
        raise ValueError("provider receipt differs from frozen operation/payload")
    record_id = provider.get("record_id")
    if not isinstance(record_id, str) or not record_id or effect.get("record_id") is not None and effect["record_id"] != record_id:
        raise ValueError("provider receipt has invalid record identity")
    if after.get("record_id") != record_id or not isinstance(after.get("fields"), dict) or any(not same_json(after["fields"].get(k), v) or k not in after["fields"] for k, v in effect["payload"].items()):
        raise ValueError("independent readback differs from frozen payload")


def validate(root, run_id):
    path = run_path(root, run_id)
    errors, structural, checks = [], [], {}
    try:
        name = workflow_name(path, root)
        proposed = proposal(path)
        text = regular(path / "01_review.md").read_text()
        starter = regular(root / "_templates/run/01_review.md").read_text()
        body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
        starter_body = re.sub(r"\A---\n.*?\n---\n", "", starter, flags=re.S)
        content = [line for line in body.splitlines() if line.strip() and not line.startswith("#")]
        if not content or body.strip() == starter_body.strip() or all(line in starter_body for line in content):
            raise ValueError("review needs an actual deliverable or explicit gap report")
        doc = binding(path, name)
        source_files(path, doc)
        policy = read_json(root / "_shared/policy.json")
        if not isinstance(policy, dict) or policy.get("mode") not in ("example", "live"):
            raise ValueError("configured policy mode must be example or live")
        effect_errors = check_effects(path, name, doc, proposed, policy)
        structural += effect_errors
        snapshot(root, path)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
        return {"can_review": False, "report_complete": False, "ready_for_effects": False, "errors": [str(exc)]}
    sources = doc["sources"]
    errors += configuration_errors(name, policy)
    errors += [g["name"] + ": " + g["reason"] for g in doc["unavailable_sources"]]
    errors += ["missing required source: " + key for key in sorted(REQUIRED[name] - set(sources))]
    def source(key):
        return inside(path, sources[key], directory=True)
    try:
        from coverage_check import stamp, load_queries, check as coverage, quarter_bounds
        since = stamp(doc["started_at"])
        zone = ZoneInfo(policy["identity"]["timezone"])
        day = since.astimezone(zone).date()
        queries, mail_evidence, contact_evidence = [], None, {}
        if "calls" in sources:
            queries, query_errors = load_queries(source("calls"), since)
            errors += query_errors
        if "mail" in sources:
            if "calls" not in sources:
                errors.append("mail statistics require paired calls")
            else:
                from mail_evidence import load_mail_evidence
                mail = source("mail")
                paths = sorted(mail.rglob("*.json")) if mail.is_dir() else [mail]
                checked = load_mail_evidence(paths, source("calls"), since, owner_id=policy["identity"]["owner_id"], timezone_name=policy["identity"]["timezone"])
                mail_evidence = checked
                checks["mail"] = checked["ready"]
                errors += checked["errors"]
                if checked["ready"]:
                    from mail_contact_stats import contact_stats
                    contacts = contact_stats(checked["messages"], policy["identity"]["owner_email"], policy["identity"]["internal_domains"],
                                             checked["addresses"], complete=True, history_complete=checked["history_complete"])
                    contact_evidence = {c["email"]:c for c in contacts}
                    errors += [c["email"] + ": " + problem for c in contacts for problem in c["errors"]]
        if name == "sales-call-prep" and "selected_call" in sources:
            selected = read_json(source("selected_call"))
            if not isinstance(selected, dict) or not selected.get("source_refs") or not selected.get("call_id"):
                errors.append("selected_call needs call_id and source_refs")
        if name == "interaction-sync":
            request = (path / "request.md").read_text()
            if not re.search(r"^interaction_id: [a-zA-Z0-9_-]+:\S+$", request, re.M):
                errors.append("request needs a persisted namespaced interaction_id")
            if "interaction" in sources and not source("interaction").read_text().strip():
                errors.append("interaction source is empty")
            if "reconciliation" in sources:
                reconciliation = read_json(source("reconciliation"))
                if not isinstance(reconciliation, dict) or not reconciliation.get("source_refs") or not isinstance(reconciliation.get("people"), list):
                    errors.append("reconciliation needs people and source_refs")
                else:
                    for person in reconciliation["people"]:
                        if not isinstance(person, dict) or not person.get("source_refs") or person.get("status") not in ("matched", "proposed", "unresolved"):
                            errors.append("invalid person reconciliation")
                        elif person["status"] == "unresolved":
                            errors.append("person identity remains unresolved")
        if name in ("pipeline-review", "forecast-weekly") and REQUIRED[name] <= set(sources):
            scope = "forecast" if name == "forecast-weekly" else "pipeline-daily" if doc["mode"] == "daily" else "pipeline"
            covered = coverage(source("calls"), policy, since, scope)
            checks["coverage"] = covered
            errors += covered["errors"]
            census = {}
            for key, obj in (("opportunities", "Opportunity"), ("tasks", "Task"), ("events", "Event")):
                actual = rows(source(key))
                census[key] = actual
                selected = [q for q in queries if q.get("source") == "crm" and q.get("object") == obj
                            and q.get("owner_id") == policy["identity"]["owner_id"]
                            and q.get("selection") == ("all_owned_open" if obj == "Opportunity" else "linked_accounts_and_opportunities")]
                expected = {}
                for q in selected:
                    for row in q["records"]:
                        if row["Id"] in expected and not same_json(expected[row["Id"]], row):
                            errors.append(key + ": conflicting receipt copies")
                        expected[row["Id"]] = row
                if not same_json({r["Id"]: r for r in actual}, expected):
                    errors.append(key + ": source census differs from paired receipts")
            from hygiene_check import evaluate as hygiene
            checked = hygiene(census["opportunities"], census["tasks"], census["events"], policy, as_of=since)
            checks["hygiene"] = checked
            errors += checked["errors"]
            if name == "forecast-weekly":
                from forecast_math import calculate
                forecast = read_json(source("forecast"))
                calculated = calculate(forecast, policy)
                checks["forecast"] = calculated
                errors += calculated["errors"]
                if not calculated["complete"]:
                    errors.append("forecast calculation incomplete")
                start, end, following = quarter_bounds(day, policy["forecast"])
                expected_target = policy["forecast"]["targets"].get(start.isoformat(), policy["forecast"].get("target_default"))
                from decimal import Decimal
                target = forecast.get("target")
                if (target is None) != (expected_target is None) or target is not None and Decimal(str(target)) != Decimal(str(expected_target)):
                    errors.append("forecast target differs from configured quarter target")
                if forecast.get("quarter_start") != start.isoformat() or forecast.get("quarter_end") != end.isoformat():
                    errors.append("forecast quarter differs from reporting calendar")
                expected_ids = set(covered.get("in_scope_ids", [])) | set(covered.get("booked_ids", []))
                if set(calculated["row_ids"]) != expected_ids:
                    errors.append("forecast rows do not match complete covered populations")
                opportunity_by_id = {r["Id"]: r for r in census["opportunities"]}
                booked_by_id = {r["Id"]: r for q in queries if q.get("selection") == "booked_in_quarter" for r in q["records"]}
                for row in forecast.get("rows", []):
                    key = row.get("deal_id")
                    expected_population = "booked" if key in covered.get("booked_ids", []) else "current" if key in opportunity_by_id and opportunity_by_id[key]["CloseDate"] < end.isoformat() else "next"
                    if row.get("population") != expected_population:
                        errors.append(str(key) + ": incorrect forecast population")
                    original = booked_by_id.get(key, opportunity_by_id.get(key, {})).get("Amount")
                    assessed = row.get("amount")
                    if isinstance(original, bool) or (assessed is None) != (original is None) or assessed is not None and Decimal(str(assessed)) != Decimal(str(original)):
                        errors.append(str(key) + ": assessed amount differs from CRM receipt")
        if name == "task-triage-speed-run" and {"tasks", "triage"} <= set(sources):
            from triage_check import evaluate
            triage = read_json(source("triage"))
            # Exact effects own draft content; feed the same values to grouping.
            drafts = {}
            draft_fields = {"to", "cc", "bcc", "subject", "body", "attachments"}
            for effect in doc["effects"]:
                if effect.get("operation") == "draft":
                    thread_id = effect["payload"].get("thread_id")
                    if thread_id in drafts:
                        errors.append("one unsent draft effect per selected thread; reconcile duplicates")
                    drafts[thread_id] = effect["payload"]
            for task in triage.get("tasks", []):
                if isinstance(task, dict) and task.get("thread_id") in drafts:
                    payload = {k: v for k, v in drafts[task["thread_id"]].items() if k in draft_fields}
                    if task.get("draft") is not None and task["draft"] != payload:
                        errors.append(str(task.get("task_id")) + ": triage draft differs from exact effect payload")
                    task["draft"] = payload
            checked = evaluate(triage, policy, since)
            checks["triage"] = checked
            errors += checked["errors"]
            if not checked["complete"]:
                errors.append("triage facts contain unresolved required evidence")
            if set(checked["task_ids"]) != {r["Id"] for r in rows(source("tasks"))}:
                errors.append("triage rows do not match selected Task census")
            census = {r["Id"]: r for r in rows(source("tasks"))}
            selected = [q for q in queries if q.get("source") == "crm" and q.get("object") == "Task"
                        and q.get("selection") == "selected_tasks" and q.get("owner_id") == policy["identity"]["owner_id"]]
            receipt_rows = {r["Id"]: r for q in selected for r in q["records"]}
            if not selected or not same_json(census, receipt_rows) or set().union(*(set(q.get("task_ids", [])) for q in selected)) != set(census):
                errors.append("selected Task census differs from paired receipt selection")
            if mail_evidence and mail_evidence["ready"]:
                from mail_contact_stats import contact_stats, addrs
                owner = policy["identity"]["owner_email"].lower()
                for task in triage["tasks"]:
                    thread = [m for m in mail_evidence["messages"] if m["thread_id"] == task["thread_id"]]
                    correspondents = set().union(*(addrs(m["from_"]) | addrs(m.get("to")) | addrs(m.get("cc")) for m in thread)) if thread else set(mail_evidence["addresses"])
                    correspondents &= set(mail_evidence["addresses"])
                    selected_contact = task.get("contact_email")
                    if selected_contact:
                        correspondents &= {selected_contact.lower()}
                    if len(correspondents) != 1 or task["mailbox"].lower() != owner:
                        errors.append(task["task_id"] + ": selected-thread correspondent/mailbox unresolved")
                        continue
                    contact = next(iter(correspondents))
                    if task["relationship"] == "cold" and contact_evidence[contact]["has_substantive_reply"] is True:
                        errors.append(task["task_id"] + ": cold relationship contradicts substantive contact history")
                    stats = contact_stats(thread, owner, policy["identity"]["internal_domains"], correspondents,
                                          complete=True, history_complete=mail_evidence["history_complete"])[0]
                    errors += [task["task_id"] + ": " + e for e in stats["errors"]]
                    for fact, calculated in (("last_sent_at", "last_sent"), ("last_reply_at", "last_substantive_reply")):
                        actual, expected = task.get(fact), stats[calculated]
                        if (actual is None) != (expected is None) or actual is not None and stamp(actual) != stamp(expected):
                            errors.append(task["task_id"] + ": " + fact + " differs from selected-thread evidence")
                    if task.get("unanswered_count") != stats["unanswered_count"]:
                        errors.append(task["task_id"] + ": unanswered_count differs from selected-thread evidence")
                    if task.get("bodies_complete") is True and any(not any(isinstance(m.get(k), str) for k in ("body_text", "body")) for m in thread):
                        errors.append(task["task_id"] + ": complete bodies were claimed but not saved")
                    if task["thread_id"] in drafts:
                        recipients = addrs(drafts[task["thread_id"]]["to"])
                        if not correspondents <= recipients or not recipients <= set(mail_evidence["addresses"]):
                            errors.append(task["task_id"] + ": draft recipients differ from selected contact history")
                        parent = drafts[task["thread_id"]]["reply_to_message_id"]
                        if parent is not None and parent not in {m["email_id"] for m in thread}:
                            errors.append(task["task_id"] + ": draft parent message is outside the selected thread")
            draft_threads = {r["thread_id"] for r in triage["tasks"] if any(t["task_id"] == r["task_id"] and t["group"] == "draft" for t in checked["tasks"])}
            if any(e.get("operation") == "draft" and e["payload"].get("thread_id") not in draft_threads for e in doc["effects"]):
                errors.append("draft effect is not eligible under the recomputed triage decision")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
        errors.append("input check: " + str(exc))
    return {"can_review": not structural, "report_complete": not errors and not structural,
            "ready_for_effects": not errors and not structural, "errors": structural + errors, "checks": checks}


def run_path(root, run_id):
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run ID must be 1-80 lowercase letters, digits or hyphens")
    path = root / "output" / run_id
    if (root / "output").is_symlink() or path.is_symlink():
        raise ValueError("run directory must not be a symlink")
    return path


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or symlinked file: " + str(path))
    return path


def init(root, run_id, workflow):
    if workflow not in load_routes(root):
        raise ValueError("unknown workflow: " + workflow)
    dest = run_path(root, run_id)
    if dest.exists():
        raise ValueError("run already exists; select a fresh task-supplied ID")
    source = root / "_templates/run"
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("run starter contains a symlink")
    dest.parent.mkdir(exist_ok=True)
    shutil.copytree(source, dest)
    regular(dest / "request.md").write_text(
        f"---\nrun_id: {run_id}\nworkflow: {workflow}\n---\n\n"
        "# Request\n\nRecord the user's request, exact scope, and input paths here before work.\n"
    )
    return dest


def workflow_name(path, root):
    text = regular(path / "request.md").read_text()
    match = re.search(r"^workflow: ([a-z0-9-]+)$", text, re.M)
    identity = re.search(r"^run_id: ([a-z0-9-]+)$", text, re.M)
    if not match or match[1] not in load_routes(root) or not identity or identity[1] != path.name:
        raise ValueError("request must identify this run and a known workflow")
    return match[1]


def snapshot(root, path):
    name = workflow_name(path, root)
    route = load_routes(root)[name]
    files = [path / "request.md", path / "01_review.md", root / "_shared/policy.json",
             root / "_shared/rules.md", root / "workflows/run.md", root / route["workspace"], root / route["workflow"]]
    files += [root / "AGENTS.md", root / "scripts/wrapper-contract.json", root / "scripts/runs.py", root / "scripts/wrappers.py"]
    files += [root / ref for ref in route["review_inputs"]]
    doc = binding(path, name)
    files += list(source_files(path, doc))
    # Each repo names additional stable inputs in the policy's review_inputs.
    policy = json.loads(regular(root / "_shared/policy.json").read_text())
    for ref in policy.get("review_inputs", []):
        rel = Path(ref)
        if rel.is_absolute() or ".." in rel.parts or not str(rel).startswith("_shared/"):
            raise ValueError("review inputs must be paths inside _shared/")
        safe_path(root, str(rel))
        files.append(root / rel)
    for ref in review_metadata(path).get("artifacts", []):
        rel = Path(ref)
        if rel.is_absolute() or ".." in rel.parts or ref in ("review.json", "02_result.json"):
            raise ValueError("review artifacts must be source or output files inside this run")
        target = path / rel
        if any((path / p).is_symlink() for p in [rel] + list(rel.parents)):
            raise ValueError("review artifact path must not contain symlinks")
        files.append(target)
    result = {str(p.relative_to(root)): hashlib.sha256(regular(p).read_bytes()).hexdigest() for p in files}
    for ref in doc["sources"].values():
        directory = path / ref
        if directory.is_dir():
            inventory = sorted(str(p.relative_to(directory)) for p in directory.rglob("*"))
            result[str(directory.relative_to(root)) + "/"] = hashlib.sha256(json.dumps(inventory).encode()).hexdigest()
    return result


def review_metadata(path):
    text = regular(path / "01_review.md").read_text()
    header = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not header:
        raise ValueError("review needs flat YAML frontmatter")
    meta = {}
    for line in header[1].splitlines():
        key, sep, value = line.partition(": ")
        if not sep or key not in ("status", "expected_after", "artifacts") or key in meta:
            raise ValueError("invalid or duplicate review metadata field")
        meta[key] = value if key == "status" else json.loads(value)
    artifacts = meta.get("artifacts", [])
    if not isinstance(artifacts, list) or any(not isinstance(v, str) or not v for v in artifacts):
        raise ValueError("artifacts must be a JSON list of run-relative paths")
    if len(artifacts) != len(set(artifacts)):
        raise ValueError("duplicate review artifact path")
    return meta


def proposal(path):
    text = regular(path / "01_review.md").read_text()
    if review_metadata(path).get("status") != "ready":
        raise ValueError("review artifact is still draft; finish the workflow's checks first")
    ids = re.findall(r"^## Effect ([a-zA-Z0-9-]+)$", text, re.M)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate effect IDs")
    return ids


def expected_after(path, effect_ids, before):
    changes = review_metadata(path).get("expected_after", {})
    if not isinstance(changes, dict) or not set(changes) <= set(proposal(path)):
        raise ValueError("expected_after must map proposed effect IDs to file hashes")
    expected = {}
    for effect, files in changes.items():
        if not isinstance(files, dict):
            raise ValueError("expected_after file revisions must be objects")
        for ref, digest in files.items():
            if ref not in before or not ref.startswith("_shared/") or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("expected_after must hash a declared shared input")
            if effect in effect_ids:
                if ref in expected and expected[ref] != digest:
                    raise ValueError("conflicting postimages for " + ref)
                expected[ref] = digest
    return expected


def record_review(root, run_id, reviewer, approval_ref, effect_ids):
    path = run_path(root, run_id)
    proposed = proposal(path)
    if not reviewer.strip() or not approval_ref.strip():
        raise ValueError("a reviewer and actual conversation reference are required")
    if len(effect_ids) != len(set(effect_ids)) or not set(effect_ids) <= set(proposed):
        raise ValueError("approved effects must be unique IDs in the reviewed proposal")
    checked = validate(root, run_id)
    if not checked["can_review"] or effect_ids and not checked["ready_for_effects"]:
        raise ValueError("review validation failed: " + "; ".join(checked["errors"]))
    previous = read_json(path / "02_result.json")
    if any(e.get("status") == "pending" and e.get("attempt_started_at") for e in previous.get("effects", [])):
        raise ValueError("reconcile pending attempts before replacing their review")
    if previous.get("recorded_at"):
        artifacts = review_metadata(path).get("artifacts", [])
        saved = [inside(path, ref).read_bytes() for ref in artifacts]
        if (path / "02_result.json").read_bytes() not in saved:
            raise ValueError("preserve the previous result as a declared artifact before replacing review")
        prior_refs = [e.get(key) for e in previous.get("effects", []) for key in ("preimage_reference", "provider_reference", "readback_reference")]
        if any(isinstance(ref, str) and ref.startswith("effect-evidence/") and ref not in artifacts for ref in prior_refs):
            raise ValueError("preserve prior apply evidence as declared artifacts before replacing review")
    before = snapshot(root, path)
    after = expected_after(path, effect_ids, before)
    doc = {"reviewer": reviewer, "approval_reference": approval_ref,
           "reviewed_at": datetime.now(timezone.utc).isoformat(),
           "approved_effect_ids": effect_ids, "snapshot": before, "expected_after": after}
    atomic_json(path / "review.json", doc)
    return doc


def _status(root, run_id):
    path = run_path(root, run_id)
    workflow_name(path, root)
    try:
        proposed = proposal(path)
    except ValueError as exc:
        return {"state": "draft", "reason": str(exc)}
    doc = json.loads(regular(path / "review.json").read_text())
    if not doc.get("reviewer") or not doc.get("approval_reference"):
        return {"state": "awaiting_human_review"}
    try:
        current = snapshot(root, path)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"state": "review_stale", "reason": str(exc)}
    before = doc.get("snapshot") or {}
    approved = doc.get("approved_effect_ids")
    if not isinstance(approved, list) or len(approved) != len(set(approved)) or not set(approved) <= set(proposed):
        raise ValueError("review contains invalid effect IDs")
    after = expected_after(path, approved, before)
    if doc.get("expected_after", {}) != after:
        return {"state": "review_stale"}
    changed = {ref for ref in current if current[ref] != before.get(ref)}
    if set(before) != set(current) or any(current[ref] != after.get(ref) for ref in changed):
        return {"state": "review_stale"}
    result = json.loads(regular(path / "02_result.json").read_text())
    if any(e.get("status") == "pending" and e.get("attempt_started_at") for e in result.get("effects", [])):
        return {"state": "recovery_required", "reason": "uncertain provider attempt; reconcile before retrying"}
    if not result.get("recorded_at"):
        return {"state": "recovery_required" if changed else "review_current", "approved_effect_ids": approved}
    if result.get("review_snapshot") != doc["snapshot"]:
        return {"state": "result_stale"}
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise ValueError("result needs a summary")
    effects = result.get("effects")
    if not isinstance(effects, list) or any(not isinstance(e, dict) for e in effects):
        raise ValueError("result effects must be objects")
    ids = [e.get("id") for e in effects]
    if len(ids) != len(set(ids)) or set(ids) != set(approved):
        raise ValueError("result must account for exactly the approved effects")
    for row in effects:
        if row.get("status") not in ("verified", "pending", "failed", "skipped"):
            raise ValueError("invalid effect result status")
        if row["status"] == "verified" and (not row.get("provider_reference") or not row.get("readback_reference")):
            raise ValueError("verified result needs provider and readback references")
        if row["status"] == "verified":
            effect = next(e for e in binding(path, workflow_name(path, root))["effects"] if e["id"] == row["id"])
            check_readback(path, effect, row, doc["reviewed_at"])
    incomplete = [e["id"] for e in effects if e["status"] != "verified"]
    if any(current[ref] != digest for ref, digest in after.items()):
        return {"state": "incomplete", "reason": "approved local file revisions have not all landed"}
    return {"state": "incomplete" if incomplete else "completion_recorded",
            "unresolved_effect_ids": incomplete,
            "note": "Local records do not prove human authorization or provider success. Inspect the cited evidence."}


def status(root, run_id):
    checked = validate(root, run_id)
    return {**_status(root, run_id), **checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    start = subs.add_parser("init")
    start.add_argument("run_id")
    start.add_argument("workflow")
    show = subs.add_parser("status")
    show.add_argument("run_id")
    check = subs.add_parser("validate")
    check.add_argument("run_id")
    review = subs.add_parser("record-review")
    review.add_argument("run_id")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--approval-ref", required=True)
    review.add_argument("--effects", nargs="*", default=[])
    args = parser.parse_args()
    try:
        if args.action == "init":
            print(init(ROOT, args.run_id, args.workflow))
        elif args.action == "status":
            print(json.dumps(status(ROOT, args.run_id), indent=2))
        elif args.action == "validate":
            checked = validate(ROOT, args.run_id)
            print(json.dumps(checked, indent=2, default=str))
            return int(not checked["report_complete"])
        else:
            record_review(ROOT, args.run_id, args.reviewer, args.approval_ref, args.effects)
            print("Review reference recorded. This command cannot grant authorization.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
