#!/usr/bin/env python3
"""Build the normalized pilot-usage input from saved warehouse results plus the approved review file.

Usage:
    python assemble_pilot_usage_input.py --review review.json --policy _shared/policy.json \
        --output /tmp/pilot-usage/input.json \
        --results results.json  # or --tool-calls <this-run>/warehouse-calls

Reads the saved Snowflake calls whose SQL carries the markers `-- pilot_usage q1_roster`,
`-- pilot_usage q4_grants`, and `-- pilot_usage q5_tasks` (newest completed result per marker,
every saved result page of that handle merged in partition order).
Reads the review file the user approved in chat. Writes one input JSON for
compute_pilot_usage_report.py. Nothing here talks to a connector.

Review file keys:
    customer_name, prepared_by, pilot_end (ISO), approved (bool)
    optional: pilot_start (default: earliest non-voided grant), data_through (default: yesterday),
              confidentiality_label, display_names {email: name}, participation_notes {email: text}
    categories: [{category_id, label, description}]
    task_categories: {context_uuid: category_id}   missing -> policy uncategorized id
    narratives: {scope_note, usage_highlights[{label,text}], representative_work[{title,user_emails,summary}],
                 work_interpretation[str], business_value[{label,text}], source_note}
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from pilot_usage_local_storage import require_local_only_output_path
from pilot_usage_policy import load_pilot_usage_policy

MARKERS = ("q1_roster", "q4_grants", "q5_tasks")
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
    # Legacy completed replies have no status; column metadata and complete
    # row/partition checks below still apply. A submission handle is not a result.
    return isinstance(result.get("data"), list)


def _merge_partitions(handle: str, pages: dict[int, tuple[float, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Concatenate one handle's saved result pages. Only page 0 carries column metadata."""
    ordered = [pages[index][1] for index in sorted(pages)]
    metadata = next((page["result_set_meta_data"] for page in ordered if page.get("result_set_meta_data")), None)
    if metadata is None:
        raise RuntimeError(f"no saved result page with column metadata for {handle}")
    expected_pages = int(ordered[0].get("total_partitions") or len(ordered))
    if sorted(pages) != list(range(expected_pages)):
        raise RuntimeError(
            f"saved result pages incomplete for {handle}: have {sorted(pages)}, expected {expected_pages}"
        )
    data = [row for page in ordered for row in page["data"]]
    expected_rows = ordered[0].get("total_row_count")
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
        statement = str(call.get("arguments", {}).get("input", {}).get("statement", ""))
        marker = next((m for m in MARKERS if f"-- pilot_usage {m}" in statement), None)
        if marker is None:
            continue
        output_path = input_path.with_name(input_path.name.replace("input_", "output_", 1))
        if not output_path.is_file():
            raise RuntimeError(f"missing saved query response: {input_path.name}")
        handle = (_load(output_path).get("result") or {}).get("statement_handle")
        if handle:
            handles[marker].append((output_path.stat().st_mtime, handle))
        else:
            raise RuntimeError(f"missing query handle for marker {marker}: {output_path.name}")

    selected = {}
    for marker, candidates in handles.items():
        if not candidates:
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
        handle = result.get("statement_handle")
        if handle not in selected.values():
            continue
        mtime = output_path.stat().st_mtime
        if not _result_ready(saved, result, output_path):
            if result.get("status") is not None:
                pending[handle] = max(pending.get(handle, 0), mtime)
            continue
        partition = int(result.get("partition") or 0)
        pages = completed.setdefault(handle, {})
        if partition not in pages or pages[partition][0] < mtime:
            pages[partition] = (mtime, result)

    rows: dict[str, list[dict[str, Any]]] = {}
    for marker, latest in selected.items():
        if latest not in completed or not any(page.get("result_set_meta_data") for _, page in completed[latest].values()):
            raise RuntimeError(f"no completed saved result for marker {marker}")
        if pending.get(latest, 0) >= max(mtime for mtime, _ in completed[latest].values()):
            raise RuntimeError(f"latest saved query result is not complete for marker {marker}")
        rows[marker] = _merge_partitions(latest, completed[latest])
    return rows


def _round_half_up(value: str | float | int) -> int:
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _parse_day(value: str) -> date:
    return datetime.fromisoformat(str(value)[:19]).date()


def assemble_input(
    results: dict[str, list[dict[str, Any]]], review: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    approved = review.get("approved") is True
    if not isinstance(review.get("approved"), bool):
        raise ValueError("approved must be a JSON boolean, backed by the conversation review")
    data_through = date.fromisoformat(
        review.get("data_through") or (date.today() - timedelta(days=1)).isoformat()
    )

    grants = [
        g for g in results["q4_grants"]
        if g.get("voided_at") is None and _parse_day(g["effective_at"]) <= data_through
    ]
    if not grants:
        raise RuntimeError("no non-voided credit grants effective on or before data_through")
    pilot_start = date.fromisoformat(
        review.get("pilot_start") or min(_parse_day(g["effective_at"]) for g in grants).isoformat()
    )
    grants_dollars = sum(Decimal(str(g["amount_dollars"])) for g in grants)

    display_names: dict[str, str] = review.get("display_names", {})
    notes: dict[str, str] = review.get("participation_notes", {})
    internal = set(policy.get("internal_domains", []))
    roster_emails = [r["user_email"].lower() for r in results["q1_roster"]
                     if r["user_email"].lower().rsplit("@", 1)[-1] not in internal]
    if len(roster_emails) != len(set(roster_emails)):
        raise ValueError("duplicate roster email")
    roster = [
        {
            "user_id": email,
            "display_name": display_names.get(email, email.split("@")[0]),
            "participation_note": notes.get(email, ""),
        }
        for email in roster_emails
    ]
    known = set(roster_emails)

    uncategorized_id = policy["uncategorized_category_id"]
    categories = list(review["categories"])
    if all(c["category_id"] != uncategorized_id for c in categories):
        categories.append(
            {"category_id": uncategorized_id, "label": "Uncategorized",
             "description": "Untitled or insufficient-evidence tasks."}
        )
    task_categories: dict[str, str] = review.get("task_categories", {})

    sessions = []
    billed_cents = Decimal(0)
    for task in results["q5_tasks"]:
        if task["user_email"].lower().rsplit("@", 1)[-1] in internal:
            continue
        task = {**task, "user_email": task["user_email"].lower()}
        if Decimal(str(task["amount_cents"])) < 0:
            raise ValueError("task billed amount must be non-negative")
        if task["user_email"] not in known:
            raise RuntimeError(f"task user is not on the roster: {task['user_email']}")
        billed_cents += Decimal(str(task["amount_cents"]))
        sessions.append(
            {
                "context_uuid": task["context_uuid"],
                "user_id": task["user_email"],
                "date": str(task["first_date"])[:10],
                "credits": _round_half_up(task["amount_cents"]),
                "category_id": task_categories.get(task["context_uuid"], uncategorized_id),
                "task_title": (task.get("task_title") or "").strip(),
                "classification_reviewed": approved,
            }
        )
    credits_used = sum(s["credits"] for s in sessions)

    narratives = review["narratives"]
    representative_work = [
        {"title": card["title"], "user_ids": list(card["user_emails"]), "summary": card["summary"]}
        for card in narratives.get("representative_work", [])
    ]

    return {
        "schema_version": 1,
        "report": {
            "customer_name": review["customer_name"],
            "prepared_date": date.today().isoformat(),
            "prepared_by": review["prepared_by"],
            "pilot_start": pilot_start.isoformat(),
            "pilot_end": review["pilot_end"],
            "data_through": data_through.isoformat(),
            "total_granted_credits": _round_half_up(grants_dollars * 100),
            "confidentiality_label": review.get("confidentiality_label", "Confidential"),
        },
        "organization_scopes": [
            {"organization_uuid": review["organization_uuid"], "workspace_role": "pilot org",
             "reviewed": approved}
        ],
        "roster": roster,
        "categories": categories,
        "sessions": sessions,
        "supplemental_undated_sessions": [],
        "source_reconciliation": {
            "eligible_context_count": len(sessions),
            "billed_amount_cents": credits_used,
            "billed_amount_cents_raw": str(billed_cents),
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
    source.add_argument("--tool-calls", type=Path, help="explicit directory of saved warehouse calls")
    source.add_argument("--results", type=Path, help="complete normalized q1_roster/q4_grants/q5_tasks results")
    args = parser.parse_args()

    policy = load_pilot_usage_policy(args.policy)
    review = _load(args.review)
    results = load_marked_results(args.tool_calls) if args.tool_calls else _load(args.results)
    normalized = assemble_input(results, review, policy)
    output_path = require_local_only_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    uncategorized = sum(
        1 for s in normalized["sessions"] if s["category_id"] == policy["uncategorized_category_id"]
    )
    print(json.dumps({
        "tasks": len(normalized["sessions"]),
        "credits_used": normalized["source_reconciliation"]["billed_amount_cents"],
        "granted_credits": normalized["report"]["total_granted_credits"],
        "seats": len(normalized["roster"]),
        "uncategorized_tasks": uncategorized,
        "pilot_start": normalized["report"]["pilot_start"],
        "data_through": normalized["report"]["data_through"],
        "approved": review.get("approved", False),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
