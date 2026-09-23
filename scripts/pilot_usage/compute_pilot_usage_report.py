#!/usr/bin/env python3
"""Compute a reconciled pilot usage report from one normalized local-only payload.

Usage:
    python compute_pilot_usage_report.py --input input.json --policy _shared/policy.json --output report.json"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import NewType, TypedDict, cast

from pilot_usage_local_storage import require_local_only_output_path
from pilot_usage_policy import load_pilot_usage_policy

PilotUserId = NewType("PilotUserId", str)
ProductContextUuid = NewType("ProductContextUuid", str)
PilotUsageCategoryId = NewType("PilotUsageCategoryId", str)


class PilotReportMetadata(TypedDict):
    customer_name: str
    prepared_date: str
    prepared_by: str
    pilot_start: str
    pilot_end: str
    data_through: str
    total_granted_credits: int
    confidentiality_label: str


class PilotOrganizationScope(TypedDict):
    organization_uuid: str
    workspace_role: str
    reviewed: bool


class PilotRosterUser(TypedDict, total=False):
    user_id: str
    display_name: str
    provisioned_date: str
    participation_note: str


class PilotUsageCategory(TypedDict):
    category_id: str
    label: str
    description: str


class PilotDatedSession(TypedDict):
    context_uuid: str
    user_id: str
    date: str
    credits: int
    category_id: str
    task_title: str
    classification_reviewed: bool


class PilotUndatedSession(TypedDict):
    context_uuid: str
    user_id: str
    credits: int
    category_id: str
    task_title: str
    classification_reviewed: bool
    reviewed: bool
    review_note: str


class PilotSourceReconciliation(TypedDict):
    eligible_context_count: int
    billed_amount_cents: int
    billed_amount_cents_raw: str


class LabeledNarrative(TypedDict):
    label: str
    text: str


class RepresentativeWorkNarrative(TypedDict):
    title: str
    user_ids: list[str]
    summary: str


class PilotReviewedNarratives(TypedDict):
    reviewed: bool
    scope_note: str
    usage_highlights: list[LabeledNarrative]
    representative_work: list[RepresentativeWorkNarrative]
    work_interpretation: list[str]
    business_value: list[LabeledNarrative]
    source_note: str


class PilotUsageInput(TypedDict):
    schema_version: int
    report: PilotReportMetadata
    organization_scopes: list[PilotOrganizationScope]
    roster: list[PilotRosterUser]
    categories: list[PilotUsageCategory]
    sessions: list[PilotDatedSession]
    supplemental_undated_sessions: list[PilotUndatedSession]
    source_reconciliation: PilotSourceReconciliation
    reviewed_narratives: PilotReviewedNarratives


class PilotUsagePolicy(TypedDict):
    schema_version: int
    report_title: str
    week_one_length_days: int
    task_grain: str
    credit_unit: str
    credit_display_rule: str
    uncategorized_category_id: str
    category_palette: list[str]
    report_page_count: int
    report_page_size: str
    pdf: PilotUsagePdfPolicy


class PilotUsageFontAsset(TypedDict):
    family: str
    file_name: str
    sha256: str
    pdf_name_token: str
    local_path: str


class PilotUsageFontAssets(TypedDict):
    sans: PilotUsageFontAsset
    mono: PilotUsageFontAsset


class PilotUsagePdfPolicy(TypedDict):
    required: bool
    page_width_points: int
    page_height_points: int
    metadata_title: str
    metadata_author: str
    chromium_timeout_seconds: int
    font_assets: PilotUsageFontAssets


class PilotUsageUserRow(TypedDict):
    user_id: str
    display_name: str
    task_count: int
    week_one_tasks: int
    week_two_tasks: int
    undated_tasks: int
    credits: int
    active_days: int
    participation_note: str


class PilotDailyTaskRow(TypedDict):
    date: str
    task_count: int


class PilotUsageCategoryRow(TypedDict):
    category_id: str
    label: str
    description: str
    task_count: int
    credits: int
    share_percent: int
    share_percent_precise: str
    color: str


class PilotHeadlineMetrics(TypedDict):
    active_users: int
    seat_count: int
    task_count: int
    credits_used: int
    active_days: int
    elapsed_days: int
    granted_credits: int
    remaining_credits: int


class PilotUsagePeriods(TypedDict):
    week_one_start: str
    week_one_end: str
    week_two_start: str
    week_two_end: str
    pilot_day_number: int
    pilot_total_days: int


class PilotComputedHighlights(TypedDict):
    top_user_count: int
    top_user_credit_share_percent: int
    most_consistent_user_id: str | None
    most_consistent_active_days: int
    inactive_user_count: int
    day_one_only_user_count: int
    undated_task_count: int
    undated_credits: int


class PilotReconciliation(TypedDict):
    tasks_match: bool
    credits_match: bool
    grants_match: bool
    category_tasks_match: bool
    category_credits_match: bool


class PilotUsageReport(TypedDict):
    schema_version: int
    report_title: str
    report: PilotReportMetadata
    headline: PilotHeadlineMetrics
    periods: PilotUsagePeriods
    users: list[PilotUsageUserRow]
    daily_tasks: list[PilotDailyTaskRow]
    categories: list[PilotUsageCategoryRow]
    computed_highlights: PilotComputedHighlights
    reviewed_narratives: PilotReviewedNarratives
    reconciliation: PilotReconciliation


def parse_pilot_iso_date(value: str, field_name: str) -> date:
    """Parse an exact date so time-zone truncation never moves pilot boundaries."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date") from exc


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _validate_reviewed_pilot_input(normalized_input: PilotUsageInput) -> None:
    if normalized_input["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    if not normalized_input["organization_scopes"]:
        raise ValueError("organization_scopes must not be empty")
    for scope in normalized_input["organization_scopes"]:
        _require_non_empty(scope["organization_uuid"], "organization_uuid")
        if scope["reviewed"] is not True:
            raise ValueError("every organization scope must be explicitly reviewed")
    if normalized_input["reviewed_narratives"]["reviewed"] is not True:
        raise ValueError("reviewed_narratives must be explicitly reviewed")

    report = normalized_input["report"]
    if type(report["total_granted_credits"]) is not int or report["total_granted_credits"] < 0:
        raise ValueError("granted credits must be a non-negative integer")
    pilot_start = parse_pilot_iso_date(report["pilot_start"], "pilot_start")
    pilot_end = parse_pilot_iso_date(report["pilot_end"], "pilot_end")
    data_through = parse_pilot_iso_date(report["data_through"], "data_through")
    if not pilot_start <= data_through <= pilot_end:
        raise ValueError("data_through must fall inside the pilot window")
    if pilot_start >= pilot_end:
        raise ValueError("pilot_end must be after pilot_start")

    roster_ids = [PilotUserId(user["user_id"]) for user in normalized_input["roster"]]
    if len(roster_ids) != len(set(roster_ids)):
        raise ValueError("roster contains duplicate user_id values")
    category_ids = [
        PilotUsageCategoryId(category["category_id"])
        for category in normalized_input["categories"]
    ]
    if len(category_ids) != len(set(category_ids)):
        raise ValueError("categories contains duplicate category_id values")

    known_users = set(roster_ids)
    known_categories = set(category_ids)
    contexts: set[ProductContextUuid] = set()
    for session in normalized_input["sessions"]:
        context_uuid = ProductContextUuid(session["context_uuid"])
        if context_uuid in contexts:
            raise ValueError(f"duplicate context_uuid: {context_uuid}")
        contexts.add(context_uuid)
        if PilotUserId(session["user_id"]) not in known_users:
            raise ValueError(
                f"session references unknown user_id: {session['user_id']}"
            )
        if PilotUsageCategoryId(session["category_id"]) not in known_categories:
            raise ValueError(
                f"session references unknown category_id: {session['category_id']}"
            )
        if session["classification_reviewed"] is not True:
            raise ValueError(f"session classification is not reviewed: {context_uuid}")
        session_date = parse_pilot_iso_date(session["date"], "session date")
        if not pilot_start <= session_date <= data_through:
            raise ValueError(
                f"session date is outside the report window: {context_uuid}"
            )
        if type(session["credits"]) is not int or session["credits"] < 0:
            raise ValueError(f"session credits must be non-negative: {context_uuid}")

    for session in normalized_input["supplemental_undated_sessions"]:
        context_uuid = ProductContextUuid(session["context_uuid"])
        if context_uuid in contexts:
            raise ValueError(f"duplicate context_uuid: {context_uuid}")
        contexts.add(context_uuid)
        if PilotUserId(session["user_id"]) not in known_users:
            raise ValueError(
                f"undated session references unknown user_id: {session['user_id']}"
            )
        if PilotUsageCategoryId(session["category_id"]) not in known_categories:
            raise ValueError(
                f"undated session references unknown category_id: {session['category_id']}"
            )
        if session["classification_reviewed"] is not True:
            raise ValueError(
                f"undated session classification is not reviewed: {context_uuid}"
            )
        if session["reviewed"] is not True or not session["review_note"].strip():
            raise ValueError(
                f"undated session requires explicit review: {context_uuid}"
            )
        if type(session["credits"]) is not int or session["credits"] < 0:
            raise ValueError(
                f"undated session credits must be non-negative: {context_uuid}"
            )

    for card in normalized_input["reviewed_narratives"]["representative_work"]:
        unknown = set(map(PilotUserId, card["user_ids"])) - known_users
        if unknown:
            raise ValueError(
                f"representative work references unknown users: {sorted(unknown)}"
            )


def _rounded_share_percent(credits: int, credits_used: int) -> int:
    if credits_used == 0:
        return 0
    share = Decimal(credits) * Decimal(100) / Decimal(credits_used)
    return int(share.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _precise_share_percent(credits: int, credits_used: int) -> str:
    if credits_used == 0:
        return "0.0"
    share = Decimal(credits) * Decimal(100) / Decimal(credits_used)
    return str(share.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def compute_pilot_usage_report(
    normalized_input: PilotUsageInput,
    policy: PilotUsagePolicy,
) -> PilotUsageReport:
    """Compute all report metrics and fail closed on source or review mismatches."""
    _validate_reviewed_pilot_input(normalized_input)
    if policy["task_grain"] != "context_uuid":
        raise ValueError("policy task_grain must be context_uuid")
    if policy["credit_unit"] != "cent":
        raise ValueError("policy credit_unit must be cent")
    if policy["credit_display_rule"] != "round_half_up_per_context_then_sum":
        raise ValueError(
            "policy credit_display_rule must be round_half_up_per_context_then_sum"
        )
    if not policy["category_palette"]:
        raise ValueError("policy category_palette must not be empty")

    report = normalized_input["report"]
    pilot_start = parse_pilot_iso_date(report["pilot_start"], "pilot_start")
    pilot_end = parse_pilot_iso_date(report["pilot_end"], "pilot_end")
    data_through = parse_pilot_iso_date(report["data_through"], "data_through")
    week_one_end = min(
        pilot_start + timedelta(days=policy["week_one_length_days"] - 1),
        data_through,
    )
    week_two_start = week_one_end + timedelta(days=1)

    dated_sessions = normalized_input["sessions"]
    undated_sessions = normalized_input["supplemental_undated_sessions"]
    all_sessions: list[PilotDatedSession | PilotUndatedSession] = [
        *dated_sessions,
        *undated_sessions,
    ]
    task_count = len(all_sessions)
    credits_used = sum(session["credits"] for session in all_sessions)
    source = normalized_input["source_reconciliation"]
    granted_credits = report["total_granted_credits"]
    if source["eligible_context_count"] != task_count:
        raise ValueError("eligible context count does not match normalized sessions")
    if source["billed_amount_cents"] != credits_used:
        raise ValueError(
            "billed AMOUNT_CENTS does not match normalized session credits"
        )
    if credits_used > granted_credits:
        raise ValueError("credits used cannot exceed granted credits")

    sessions_by_user: dict[
        PilotUserId, list[PilotDatedSession | PilotUndatedSession]
    ] = defaultdict(list)
    dated_by_user: dict[PilotUserId, list[PilotDatedSession]] = defaultdict(list)
    for session in all_sessions:
        sessions_by_user[PilotUserId(session["user_id"])].append(session)
    for session in dated_sessions:
        dated_by_user[PilotUserId(session["user_id"])].append(session)

    users: list[PilotUsageUserRow] = []
    for roster_user in normalized_input["roster"]:
        user_id = PilotUserId(roster_user["user_id"])
        user_sessions = sessions_by_user[user_id]
        user_dated_sessions = dated_by_user[user_id]
        week_one_tasks = sum(
            1
            for session in user_dated_sessions
            if pilot_start
            <= parse_pilot_iso_date(session["date"], "date")
            <= week_one_end
        )
        week_two_tasks = sum(
            1
            for session in user_dated_sessions
            if week_two_start
            <= parse_pilot_iso_date(session["date"], "date")
            <= data_through
        )
        users.append(
            {
                "user_id": str(user_id),
                "display_name": roster_user["display_name"],
                "task_count": len(user_sessions),
                "week_one_tasks": week_one_tasks,
                "week_two_tasks": week_two_tasks,
                "undated_tasks": len(user_sessions) - len(user_dated_sessions),
                "credits": sum(session["credits"] for session in user_sessions),
                "active_days": len(
                    {session["date"] for session in user_dated_sessions}
                ),
                "participation_note": roster_user.get("participation_note", ""),
            }
        )
    users.sort(
        key=lambda user: (-user["credits"], -user["task_count"], user["display_name"])
    )

    daily_counts = Counter(session["date"] for session in dated_sessions)
    elapsed_days = (data_through - pilot_start).days + 1
    daily_tasks = [
        {
            "date": (pilot_start + timedelta(days=offset)).isoformat(),
            "task_count": daily_counts[
                (pilot_start + timedelta(days=offset)).isoformat()
            ],
        }
        for offset in range(elapsed_days)
    ]

    category_task_counts = Counter(session["category_id"] for session in all_sessions)
    category_credit_counts: dict[str, int] = defaultdict(int)
    for session in all_sessions:
        category_credit_counts[session["category_id"]] += session["credits"]
    palette = policy["category_palette"]
    categories = [
        {
            "category_id": category["category_id"],
            "label": category["label"],
            "description": category["description"],
            "task_count": category_task_counts[category["category_id"]],
            "credits": category_credit_counts[category["category_id"]],
            "share_percent": _rounded_share_percent(
                category_credit_counts[category["category_id"]], credits_used
            ),
            "share_percent_precise": _precise_share_percent(
                category_credit_counts[category["category_id"]], credits_used
            ),
            "color": palette[index % len(palette)],
        }
        for index, category in enumerate(normalized_input["categories"])
    ]
    categories.sort(key=lambda category: (-category["credits"], category["label"]))

    active_users = [user for user in users if user["task_count"] > 0]
    most_consistent = max(
        active_users,
        key=lambda user: (user["active_days"], user["task_count"], user["credits"]),
        default=None,
    )
    top_user_count = min(4, len(active_users))
    top_user_credits = sum(user["credits"] for user in active_users[:top_user_count])
    day_one_only_user_count = sum(
        1
        for user in active_users
        if {session["date"] for session in dated_by_user[PilotUserId(user["user_id"])]}
        == {pilot_start.isoformat()}
    )

    category_tasks_match = (
        sum(category["task_count"] for category in categories) == task_count
    )
    category_credits_match = (
        sum(category["credits"] for category in categories) == credits_used
    )
    reconciliation: PilotReconciliation = {
        "tasks_match": sum(user["task_count"] for user in users) == task_count,
        "credits_match": sum(user["credits"] for user in users) == credits_used,
        "grants_match": granted_credits == report["total_granted_credits"],
        "category_tasks_match": category_tasks_match,
        "category_credits_match": category_credits_match,
    }
    if not all(reconciliation.values()):
        raise ValueError("computed report failed deterministic reconciliation")

    return {
        "schema_version": 1,
        "report_title": policy["report_title"],
        "report": report,
        "headline": {
            "active_users": len(active_users),
            "seat_count": len(users),
            "task_count": task_count,
            "credits_used": credits_used,
            "active_days": sum(1 for row in daily_tasks if row["task_count"] > 0),
            "elapsed_days": elapsed_days,
            "granted_credits": granted_credits,
            "remaining_credits": granted_credits - credits_used,
        },
        "periods": {
            "week_one_start": pilot_start.isoformat(),
            "week_one_end": week_one_end.isoformat(),
            "week_two_start": week_two_start.isoformat(),
            "week_two_end": data_through.isoformat(),
            "pilot_day_number": elapsed_days,
            "pilot_total_days": (pilot_end - pilot_start).days + 1,
        },
        "users": users,
        "daily_tasks": daily_tasks,
        "categories": categories,
        "computed_highlights": {
            "top_user_count": top_user_count,
            "top_user_credit_share_percent": _rounded_share_percent(
                top_user_credits, credits_used
            ),
            "most_consistent_user_id": (
                most_consistent["user_id"] if most_consistent else None
            ),
            "most_consistent_active_days": (
                most_consistent["active_days"] if most_consistent else 0
            ),
            "inactive_user_count": len(users) - len(active_users),
            "day_one_only_user_count": day_one_only_user_count,
            "undated_task_count": len(undated_sessions),
            "undated_credits": sum(session["credits"] for session in undated_sessions),
        },
        "reviewed_narratives": normalized_input["reviewed_narratives"],
        "reconciliation": reconciliation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute a reconciled pilot usage report from normalized local-only JSON."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    normalized_input = cast(
        PilotUsageInput, json.loads(args.input.read_text(encoding="utf-8"))
    )
    policy = cast(PilotUsagePolicy, load_pilot_usage_policy(args.policy))
    computed_report = compute_pilot_usage_report(normalized_input, policy)
    output_path = require_local_only_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(computed_report, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
