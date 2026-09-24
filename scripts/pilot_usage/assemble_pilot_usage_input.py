#!/usr/bin/env python3
"""Build the normalized pilot-usage input from saved analytics results plus the approved review file.

Usage:
    python assemble_pilot_usage_input.py --review review.json --policy _shared/policy.json \
        --output /tmp/pilot-usage/input.json \
        --results results.json  # or --tool-calls <this-run>/analytics-calls

Reads normalized saved analytics calls labeled with a dataset (roster, activities,
or optional allocations). Every page of each selected query must be complete.
Reads the review file the user approved in chat. Writes one input JSON for
compute_pilot_usage_report.py. Nothing here talks to a connector.

Review file keys:
    customer_name, scope_id, prepared_by, pilot_start, pilot_end, data_through (ISO), approved (bool)
    optional: confidentiality_label, display_names {user_id: name}, participation_notes {user_id: text}
    categories: [{category_id, label, description}]
    activity_categories: {activity_id: category_id}   missing -> policy uncategorized id
    narratives: {scope_note, usage_highlights[{label,text}], representative_work[{title,user_ids,summary}],
                 work_interpretation[str], business_value[{label,text}], source_note}
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pilot_usage_local_storage import require_local_only_output_path
from pilot_usage_policy import load_pilot_usage_policy, quantity_to_units, validate_metric

MARKERS = ("roster", "allocations", "activities")
PENDING_STATUSES = {"pending", "queued", "running", "submitted"}
SUCCESS_STATUSES = {"success", "succeeded"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _result_ready(saved: dict[str, Any], result: dict[str, Any], path: Path) -> bool:
    """Reject failed receipts before inspecting rows, including failures without data."""
    error = saved.get("error") or result.get("error") or result.get("errors")
    if saved.get("isError") or error:
        raise RuntimeError(f"failed saved query result {path.name}: {error or 'tool error'}")
    status = result.get("status")
    if status is not None:
        status = str(status).strip().lower()
        if status in PENDING_STATUSES:
            return False
        if status not in SUCCESS_STATUSES:
            raise RuntimeError(f"unsuccessful saved query result {path.name}: status {status!r}")
    else:
        raise RuntimeError(f"saved query result lacks terminal status: {path.name}")
    return isinstance(result.get("rows"), list)


def _merge_partitions(handle: str, pages: dict[int, tuple[float, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Concatenate one handle's saved result pages. Only page 0 carries column metadata."""
    ordered = [pages[index][1] for index in sorted(pages)]
    metadata = next((page["columns"] for page in ordered if page.get("columns")), None)
    if metadata is None:
        raise RuntimeError(f"no saved result page with column metadata for {handle}")
    expected_pages = int(ordered[0].get("page_count") or len(ordered))
    if sorted(pages) != list(range(expected_pages)):
        raise RuntimeError(
            f"saved result pages incomplete for {handle}: have {sorted(pages)}, expected {expected_pages}"
        )
    data = [row for page in ordered for row in page["rows"]]
    expected_rows = ordered[0].get("total_count")
    if expected_rows is not None and len(data) != int(expected_rows):
        raise RuntimeError(f"saved result rows for {handle} total {len(data)}, expected {expected_rows}")
    columns = [column["name"].lower() for column in metadata]
    if len(columns) != len(set(columns)) or any(len(row) != len(columns) for row in data):
        raise RuntimeError(f"invalid column or row shape for {handle}")
    return [dict(zip(columns, row)) for row in data]


def load_marked_results(tool_calls_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Return rows per marker from the newest completed saved result for that marker's handle."""
    handles: dict[str, list[tuple[float, str]]] = {marker: [] for marker in MARKERS}
    for input_path in tool_calls_dir.glob("input_*.json"):
        call = _load(input_path)
        marker = call.get("arguments", {}).get("dataset")
        if marker not in MARKERS:
            continue
        output_path = input_path.with_name(input_path.name.replace("input_", "output_", 1))
        if not output_path.is_file():
            raise RuntimeError(f"missing saved query response: {input_path.name}")
        handle = (_load(output_path).get("result") or {}).get("query_id")
        if handle:
            handles[marker].append((output_path.stat().st_mtime, handle))
        else:
            raise RuntimeError(f"missing query handle for marker {marker}: {output_path.name}")

    selected = {}
    for marker, candidates in handles.items():
        if not candidates:
            if marker == "allocations":
                continue
            raise RuntimeError(f"no saved query handle for marker {marker}")
        selected[marker] = sorted(candidates)[-1][1]

    # handle -> partition index -> (mtime, result). Newest save wins per partition.
    completed: dict[str, dict[int, tuple[float, dict[str, Any]]]] = {}
    pending: dict[str, float] = {}
    for output_path in tool_calls_dir.glob("output_*.json"):
        saved = _load(output_path)
        result = saved.get("result") or {}
        if not isinstance(result, dict):
            continue
        handle = result.get("query_id")
        if handle not in selected.values():
            continue
        mtime = output_path.stat().st_mtime
        if not _result_ready(saved, result, output_path):
            if result.get("status") is not None:
                pending[handle] = max(pending.get(handle, 0), mtime)
            continue
        partition = int(result.get("page_index") or 0)
        pages = completed.setdefault(handle, {})
        if partition not in pages or pages[partition][0] < mtime:
            pages[partition] = (mtime, result)

    rows: dict[str, list[dict[str, Any]]] = {}
    for marker, latest in selected.items():
        if latest not in completed or not any(page.get("columns") for _, page in completed[latest].values()):
            raise RuntimeError(f"no completed saved result for marker {marker}")
        if pending.get(latest, 0) >= max(mtime for mtime, _ in completed[latest].values()):
            raise RuntimeError(f"latest saved query result is not complete for marker {marker}")
        rows[marker] = _merge_partitions(latest, completed[latest])
    return rows


def _parse_day(value: str) -> date:
    return datetime.fromisoformat(str(value)[:19]).date()


def assemble_input(
    results: dict[str, list[dict[str, Any]]], review: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    approved = review.get("approved") is True
    if not isinstance(review.get("approved"), bool):
        raise ValueError("approved must be a JSON boolean, backed by the conversation review")
    metric = policy["metric"]
    validate_metric(metric)
    data_through = date.fromisoformat(review["data_through"])
    pilot_start = date.fromisoformat(review["pilot_start"])
    allocations = results.get("allocations")
    allocated_units = None if allocations is None else sum(
        quantity_to_units(row["quantity"], metric) for row in allocations
        if row.get("voided_at") is None and _parse_day(row["effective_at"]) <= data_through
    )
    if metric["enforce_allocation_limit"] and allocated_units is None:
        raise ValueError("this metric requires a verified allocation")

    display_names = review.get("display_names", {})
    notes = review.get("participation_notes", {})
    internal = {domain.lower() for domain in policy.get("internal_domains", [])}
    excluded = {row["user_id"] for row in results["roster"]
                if str(row.get("email", "")).lower().rsplit("@", 1)[-1] in internal}
    roster = [
        {"user_id": row["user_id"],
         "display_name": display_names.get(row["user_id"], row.get("display_name") or row["user_id"].split("@")[0]),
         "participation_note": notes.get(row["user_id"], "")}
        for row in results["roster"] if row["user_id"] not in excluded
    ]
    roster_ids = [row["user_id"] for row in roster]
    if any(not isinstance(value, str) or not value.strip() for value in roster_ids):
        raise ValueError("roster user_id must be a non-empty string")
    if len(roster_ids) != len(set(roster_ids)):
        raise ValueError("duplicate roster user_id")
    known = set(roster_ids)

    uncategorized_id = policy["uncategorized_category_id"]
    categories = list(review["categories"])
    if all(c["category_id"] != uncategorized_id for c in categories):
        categories.append(
            {"category_id": uncategorized_id, "label": "Uncategorized",
             "description": "Unclassified or insufficient-evidence activities."}
        )
    activity_categories: dict[str, str] = review.get("activity_categories", {})

    activities = []
    quantity_raw = Decimal(0)
    for task in results["activities"]:
        if task["user_id"] in excluded:
            continue
        units = quantity_to_units(task["quantity"], metric)
        if task["user_id"] not in known:
            raise RuntimeError(f"activity participant is not on the roster: {task['user_id']}")
        quantity_raw += Decimal(str(task["quantity"]))
        activities.append(
            {
                "activity_id": task["activity_id"],
                "user_id": task["user_id"],
                "date": date.fromisoformat(task["date"]).isoformat(),
                "usage_units": units,
                "category_id": activity_categories.get(task["activity_id"], uncategorized_id),
                "activity_title": (task.get("activity_title") or "").strip(),
                "classification_reviewed": approved,
            }
        )
    usage_units = sum(s["usage_units"] for s in activities)

    narratives = review["narratives"]
    representative_work = [
        {"title": card["title"], "user_ids": list(card["user_ids"]), "summary": card["summary"]}
        for card in narratives.get("representative_work", [])
    ]

    return {
        "schema_version": 2,
        "metric": dict(metric),
        "report": {
            "customer_name": review["customer_name"],
            "prepared_date": date.today().isoformat(),
            "prepared_by": review["prepared_by"],
            "pilot_start": pilot_start.isoformat(),
            "pilot_end": review["pilot_end"],
            "data_through": data_through.isoformat(),
            "allocated_units": allocated_units,
            "confidentiality_label": review.get("confidentiality_label", "Confidential"),
        },
        "scopes": [
            {"scope_id": review["scope_id"], "scope_role": "pilot",
             "reviewed": approved}
        ],
        "roster": roster,
        "categories": categories,
        "activities": activities,
        "undated_activities": [],
        "source_reconciliation": {
            "activity_count": len(activities),
            "usage_units": usage_units,
            "quantity_raw": str(quantity_raw),
        },
        "reviewed_narratives": {
            "reviewed": approved,
            "scope_note": narratives.get("scope_note", ""),
            "usage_highlights": narratives.get("usage_highlights", []),
            "representative_work": representative_work,
            "work_interpretation": narratives.get("work_interpretation", []),
            "business_value": narratives.get("business_value", []),
            "source_note": narratives.get("source_note", ""),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tool-calls", type=Path, help="explicit directory of saved analytics calls")
    source.add_argument("--results", type=Path, help="complete normalized roster/allocations/activities results")
    args = parser.parse_args()

    policy = load_pilot_usage_policy(args.policy)
    review = _load(args.review)
    results = load_marked_results(args.tool_calls) if args.tool_calls else _load(args.results)
    normalized = assemble_input(results, review, policy)
    output_path = require_local_only_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    uncategorized = sum(
        1 for s in normalized["activities"] if s["category_id"] == policy["uncategorized_category_id"]
    )
    print(json.dumps({
        "activities": len(normalized["activities"]),
        "usage_units": normalized["source_reconciliation"]["usage_units"],
        "allocated_units": normalized["report"]["allocated_units"],
        "participants": len(normalized["roster"]),
        "uncategorized_activities": uncategorized,
        "pilot_start": normalized["report"]["pilot_start"],
        "data_through": normalized["report"]["data_through"],
        "approved": review.get("approved", False),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
