"""Saved mail readers and explicit paired-receipt completeness; never accesses a provider."""
from datetime import timedelta, timezone, date
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os

from coverage_check import address, load_queries, reference_path, selection_error, stamp, validate_mail_row

ANNOTATIONS = {"classification", "delivery_failures"}


def timestamp(value):
    return stamp(value).astimezone(timezone.utc)


def same_message(first, second):
    """Identical conclusions can cite different raw copies of the same message."""
    def value(row):
        row = dict(row)
        if isinstance(row.get("classification"), dict):
            row["classification"] = {k:v for k,v in row["classification"].items() if k != "evidence_refs"}
        if isinstance(row.get("delivery_failures"), list):
            row["delivery_failures"] = [{k:v for k,v in failure.items() if k != "evidence_refs"} for failure in row["delivery_failures"]]
        return row
    return value(first) == value(second)


def validate_annotations(row, calls):
    classification = row.get("classification")
    if classification is not None:
        if not isinstance(classification, dict) or classification.get("kind") not in {"substantive", "ooo", "bounce", "calendar", "unknown"}:
            raise ValueError("invalid classification.kind")
        if classification.get("basis") not in {"provider_metadata", "content_review"}:
            raise ValueError("invalid classification.basis")
    failures = row.get("delivery_failures", [])
    if not isinstance(failures, list):
        raise ValueError("delivery_failures must be a list")
    for failure in failures:
        if not isinstance(failure, dict) or failure.get("status", "unknown") not in {"failed", "delayed", "unknown"}:
            raise ValueError("invalid delivery failure status")
        recipients = failure.get("recipients")
        if not isinstance(recipients, list) or not recipients:
            raise ValueError("delivery failure needs identified recipients")
        for recipient in recipients:
            address(recipient)
    for annotation in ([classification] if classification is not None else []) + failures:
        refs = annotation.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            raise ValueError("classification/delivery evidence_refs must identify saved sources")
        for ref in refs:
            reference_path(calls, ref)


def load_messages(paths, evidence_root=None):
    """Read legacy envelopes for inspection. This alone never establishes completeness."""
    messages = {}
    for path in paths:
        path = Path(path)
        try:
            doc = json.loads(path.read_text())
            if not isinstance(doc, dict):
                raise ValueError("mail envelope must be an object")
            result = doc.get("result", doc)
            if isinstance(result, str):
                result = json.loads(result)
            if not isinstance(result, dict):
                raise ValueError("mail result must be an object")
            if result.get("error") or result.get("authenticated") is False or result.get("status", "success") != "success":
                raise ValueError("failed mail result")
            envelope = result.get("email_results")
            rows = envelope.get("emails") if isinstance(envelope, dict) else None
            if not isinstance(rows, list):
                raise ValueError("missing mail rows")
            for index, row in enumerate(rows):
                try:
                    validate_mail_row(row)
                    validate_annotations(row, evidence_root or path.parent)
                    key = row["email_id"]
                    if key in messages and messages[key] != row:
                        raise ValueError("conflicting copies of message " + key)
                    messages[key] = row
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"record {index}: {exc}") from None
        except (TypeError, ValueError, OSError) as exc:
            raise ValueError(f"{path}: {exc}") from None
    return sorted(messages.values(), key=lambda row: (timestamp(row["date"]), row["email_id"]))


def load_mail_evidence(paths, calls=None, since=None, owner_id=None, addresses=None, require_all_history=True, timezone_name=None):
    """Bind exact saved envelopes to complete contact_history receipt chains.

    Paths can be empty-result envelopes. Returned messages use source-linked
    annotations on the normalized receipt rows, preserving raw provider files.
    """
    paths = [Path(os.path.abspath(path)) for path in paths]
    result = {"messages":[], "ready":False, "errors":[], "history_complete":False, "addresses":[]}
    errors = result["errors"]
    try:
        messages = load_messages(paths, evidence_root=calls)
        result["messages"] = messages
        if not paths:
            raise ValueError("at least one saved mail envelope is required, including for empty results")
        if calls is None or since is None:
            raise ValueError("mail completeness requires --calls and --since paired receipts")
        if isinstance(since, str):
            since = stamp(since)
        requested = {address(a) for a in addresses} if addresses is not None else set()
        queries, receipt_errors = load_queries(Path(calls), since)
        errors.extend(receipt_errors)
        supplied = set(paths)
        selected, matched = [], set()
        for query in queries:
            if query["source"] != "mail":
                continue
            refs = {reference_path(calls, ref) for ref in query["provider_references"]}
            if not refs & supplied:
                continue
            selected.append(query)
            matched.update(refs & supplied)
            if not refs <= supplied:
                errors.append(query["query_id"] + ": missing an envelope from the selected query chain")
            if owner_id is not None and query["owner_id"] != owner_id:
                errors.append(query["query_id"] + ": wrong mailbox owner")
        if supplied - matched or not selected:
            errors.append("mail input files do not match complete query raw-file references")
        normalized, covered, full_history_addresses = {}, set(), set()
        run_day = since.astimezone(ZoneInfo(timezone_name)).date() if timezone_name is not None else since.date()
        today_end = run_day + timedelta(days=1)
        for query in selected:
            label = query["query_id"]
            problem = selection_error(query)
            if problem or query["selection"] != "contact_history" or query.get("direction") != "both":
                errors.append(label + ": " + (problem or "requires contact_history in both directions"))
                continue
            try:
                values = query.get("addresses")
                if not isinstance(values, list) or not values:
                    raise ValueError("addresses must identify the requested contacts")
                query_addresses = {address(a) for a in values}
                beginning, ending = query["start_date"], query["end_date"]
                beginning = date.fromisoformat(beginning) if beginning is not None else None
                ending = date.fromisoformat(ending) if ending is not None else None
                if beginning is not None and ending is not None and beginning >= ending:
                    raise ValueError("empty/reversed history interval")
                if ending is not None and ending < today_end:
                    raise ValueError("history ends before the reporting day is covered")
                covered.update(query_addresses)
                if beginning is None:
                    full_history_addresses.update(query_addresses)
                for row in query["records"]:
                    validate_annotations(row, calls)
                    key = row["email_id"]
                    if key in normalized and not same_message(normalized[key], row):
                        raise ValueError("conflicting normalized copies of message " + key)
                    normalized.setdefault(key, row)
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(label + ": " + str(exc))
        requested = requested or covered
        result["addresses"] = sorted(requested)
        if not requested or not requested <= covered:
            errors.append("contact_history does not cover every requested address")
        result["history_complete"] = bool(requested) and requested <= full_history_addresses
        if require_all_history and not result["history_complete"]:
            errors.append("limited/unknown history cannot establish all-history unanswered or cold status")
        raw = {row["email_id"]:row for row in messages}
        if set(raw) != set(normalized):
            errors.append("mail envelope message IDs differ from their complete receipts")
        for key in raw.keys() & normalized.keys():
            source = {k:v for k,v in raw[key].items() if k not in ANNOTATIONS}
            receipt = {k:v for k,v in normalized[key].items() if k not in ANNOTATIONS}
            if source != receipt:
                errors.append(key + ": mail content differs from the bound receipt")
        result["messages"] = sorted(normalized.values(), key=lambda row:(timestamp(row["date"]),row["email_id"]))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(str(exc))
    result["ready"] = not errors
    return result
