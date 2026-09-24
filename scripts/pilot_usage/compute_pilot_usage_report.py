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
from pilot_usage_policy import load_pilot_usage_policy, validate_metric

PilotUserId = NewType("PilotUserId", str)
PilotActivityId = NewType("PilotActivityId", str)
PilotUsageCategoryId = NewType("PilotUsageCategoryId", str)


class PilotReportMetadata(TypedDict):
    customer_name: str
    prepared_date: str
    prepared_by: str
    pilot_start: str
    pilot_end: str
    data_through: str
    allocated_units: int | None
    confidentiality_label: str


class PilotScope(TypedDict):
    scope_id: str
    scope_role: str
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


class PilotDatedActivity(TypedDict):
    activity_id: str
    user_id: str
    date: str
    usage_units: int
    category_id: str
    activity_title: str
    classification_reviewed: bool


class PilotUndatedActivity(TypedDict):
    activity_id: str
    user_id: str
    usage_units: int
    category_id: str
    activity_title: str
    classification_reviewed: bool
    reviewed: bool
    review_note: str


class PilotSourceReconciliation(TypedDict):
    activity_count: int
    usage_units: int
    quantity_raw: str


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
    metric: dict
    report: PilotReportMetadata
    scopes: list[PilotScope]
    roster: list[PilotRosterUser]
    categories: list[PilotUsageCategory]
    activities: list[PilotDatedActivity]
    undated_activities: list[PilotUndatedActivity]
    source_reconciliation: PilotSourceReconciliation
    reviewed_narratives: PilotReviewedNarratives


class PilotUsagePolicy(TypedDict):
    schema_version: int
    report_title: str
    week_one_length_days: int
    metric: dict
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
    activity_count: int
    initial_period_activities: int
    later_activities: int
    undated_activities: int
    usage_units: int
    active_days: int
    participation_note: str


class PilotDailyActivityRow(TypedDict):
    date: str
    activity_count: int


class PilotUsageCategoryRow(TypedDict):
    category_id: str
    label: str
    description: str
    activity_count: int
    usage_units: int
    share_percent: int
    share_percent_precise: str
    color: str


class PilotHeadlineMetrics(TypedDict):
    active_users: int
    participant_count: int
    activity_count: int
    usage_units: int
    active_days: int
    elapsed_days: int
    allocated_units: int | None
    remaining_units: int | None


class PilotUsagePeriods(TypedDict):
    week_one_start: str
    week_one_end: str
    week_two_start: str
    week_two_end: str
    pilot_day_number: int
    pilot_total_days: int


class PilotComputedHighlights(TypedDict):
    top_user_count: int
    top_user_usage_share_percent: int
    most_consistent_user_id: str | None
    most_consistent_active_days: int
    inactive_user_count: int
    day_one_only_user_count: int
    undated_activity_count: int
    undated_units: int


class PilotReconciliation(TypedDict):
    counts_match: bool
    units_match: bool
    allocation_matches: bool
    category_counts_match: bool
    category_units_match: bool


class PilotUsageReport(TypedDict):
    schema_version: int
    metric: dict
    report_title: str
    report: PilotReportMetadata
    headline: PilotHeadlineMetrics
    periods: PilotUsagePeriods
    users: list[PilotUsageUserRow]
    daily_activities: list[PilotDailyActivityRow]
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
    if normalized_input["schema_version"] != 2:
        raise ValueError("schema_version must be 2")
    if not normalized_input["scopes"]:
        raise ValueError("scopes must not be empty")
    for scope in normalized_input["scopes"]:
        _require_non_empty(scope["scope_id"], "scope_id")
        if scope["reviewed"] is not True:
            raise ValueError("every pilot scope must be explicitly reviewed")
    if normalized_input["reviewed_narratives"]["reviewed"] is not True:
        raise ValueError("reviewed_narratives must be explicitly reviewed")

    report = normalized_input["report"]
    if report["allocated_units"] is not None and (type(report["allocated_units"]) is not int or report["allocated_units"] < 0):
        raise ValueError("allocated_units must be null or a non-negative integer")
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
    contexts: set[PilotActivityId] = set()
    for session in normalized_input["activities"]:
        activity_id = PilotActivityId(session["activity_id"])
        _require_non_empty(activity_id, "activity_id")
        if activity_id in contexts:
            raise ValueError(f"duplicate activity_id: {activity_id}")
        contexts.add(activity_id)
        if PilotUserId(session["user_id"]) not in known_users:
            raise ValueError(
                f"session references unknown user_id: {session['user_id']}"
            )
        if PilotUsageCategoryId(session["category_id"]) not in known_categories:
            raise ValueError(
                f"session references unknown category_id: {session['category_id']}"
            )
        if session["classification_reviewed"] is not True:
            raise ValueError(f"session classification is not reviewed: {activity_id}")
        session_date = parse_pilot_iso_date(session["date"], "session date")
        if not pilot_start <= session_date <= data_through:
            raise ValueError(
                f"session date is outside the report window: {activity_id}"
            )
        if type(session["usage_units"]) is not int or session["usage_units"] < 0:
            raise ValueError(f"session usage_units must be non-negative: {activity_id}")

    for session in normalized_input["undated_activities"]:
        activity_id = PilotActivityId(session["activity_id"])
        _require_non_empty(activity_id, "activity_id")
        if activity_id in contexts:
            raise ValueError(f"duplicate activity_id: {activity_id}")
        contexts.add(activity_id)
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
                f"undated session classification is not reviewed: {activity_id}"
            )
        if session["reviewed"] is not True or not session["review_note"].strip():
            raise ValueError(
                f"undated session requires explicit review: {activity_id}"
            )
        if type(session["usage_units"]) is not int or session["usage_units"] < 0:
            raise ValueError(
                f"undated session usage_units must be non-negative: {activity_id}"
            )

    for card in normalized_input["reviewed_narratives"]["representative_work"]:
        unknown = set(map(PilotUserId, card["user_ids"])) - known_users
        if unknown:
            raise ValueError(
                f"representative work references unknown users: {sorted(unknown)}"
            )


def _rounded_share_percent(usage_units: int, total_units: int) -> int:
    if total_units == 0:
        return 0
    share = Decimal(usage_units) * Decimal(100) / Decimal(total_units)
    return int(share.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _precise_share_percent(usage_units: int, total_units: int) -> str:
    if total_units == 0:
        return "0.0"
    share = Decimal(usage_units) * Decimal(100) / Decimal(total_units)
    return str(share.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def compute_pilot_usage_report(
    normalized_input: PilotUsageInput,
    policy: PilotUsagePolicy,
) -> PilotUsageReport:
    """Compute all report metrics and fail closed on source or review mismatches."""
    _validate_reviewed_pilot_input(normalized_input)
    validate_metric(policy["metric"])
    if normalized_input["metric"] != policy["metric"]:
        raise ValueError("input metric differs from policy; reassemble and review")
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

    dated_activities = normalized_input["activities"]
    undated_activities = normalized_input["undated_activities"]
    all_activities: list[PilotDatedActivity | PilotUndatedActivity] = [
        *dated_activities,
        *undated_activities,
    ]
    activity_count = len(all_activities)
    usage_units = sum(session["usage_units"] for session in all_activities)
    source = normalized_input["source_reconciliation"]
    allocated_units = report["allocated_units"]
    if source["activity_count"] != activity_count:
        raise ValueError("source activity count does not match normalized activities")
    if source["usage_units"] != usage_units:
        raise ValueError(
            "source usage units does not match normalized session usage_units"
        )
    if policy["metric"]["enforce_allocation_limit"] and (allocated_units is None or usage_units > allocated_units):
        raise ValueError("usage exceeds or lacks the required allocation")

    activities_by_user: dict[
        PilotUserId, list[PilotDatedActivity | PilotUndatedActivity]
    ] = defaultdict(list)
    dated_by_user: dict[PilotUserId, list[PilotDatedActivity]] = defaultdict(list)
    for session in all_activities:
        activities_by_user[PilotUserId(session["user_id"])].append(session)
    for session in dated_activities:
        dated_by_user[PilotUserId(session["user_id"])].append(session)

    users: list[PilotUsageUserRow] = []
    for roster_user in normalized_input["roster"]:
        user_id = PilotUserId(roster_user["user_id"])
        user_activities = activities_by_user[user_id]
        user_dated_activities = dated_by_user[user_id]
        initial_period_activities = sum(
            1
            for session in user_dated_activities
            if pilot_start
            <= parse_pilot_iso_date(session["date"], "date")
            <= week_one_end
        )
        later_activities = sum(
            1
            for session in user_dated_activities
            if week_two_start
            <= parse_pilot_iso_date(session["date"], "date")
            <= data_through
        )
        users.append(
            {
                "user_id": str(user_id),
                "display_name": roster_user["display_name"],
                "activity_count": len(user_activities),
                "initial_period_activities": initial_period_activities,
                "later_activities": later_activities,
                "undated_activities": len(user_activities) - len(user_dated_activities),
                "usage_units": sum(session["usage_units"] for session in user_activities),
                "active_days": len(
                    {session["date"] for session in user_dated_activities}
                ),
                "participation_note": roster_user.get("participation_note", ""),
            }
        )
    users.sort(
        key=lambda user: (-user["usage_units"], -user["activity_count"], user["display_name"])
    )

    daily_counts = Counter(session["date"] for session in dated_activities)
    elapsed_days = (data_through - pilot_start).days + 1
    daily_activities = [
        {
            "date": (pilot_start + timedelta(days=offset)).isoformat(),
            "activity_count": daily_counts[
                (pilot_start + timedelta(days=offset)).isoformat()
            ],
        }
        for offset in range(elapsed_days)
    ]

    category_activity_counts = Counter(session["category_id"] for session in all_activities)
    category_unit_counts: dict[str, int] = defaultdict(int)
    for session in all_activities:
        category_unit_counts[session["category_id"]] += session["usage_units"]
    palette = policy["category_palette"]
    categories = [
        {
            "category_id": category["category_id"],
            "label": category["label"],
            "description": category["description"],
            "activity_count": category_activity_counts[category["category_id"]],
            "usage_units": category_unit_counts[category["category_id"]],
            "share_percent": _rounded_share_percent(
                category_unit_counts[category["category_id"]], usage_units
            ),
            "share_percent_precise": _precise_share_percent(
                category_unit_counts[category["category_id"]], usage_units
            ),
            "color": palette[index % len(palette)],
        }
        for index, category in enumerate(normalized_input["categories"])
    ]
    categories.sort(key=lambda category: (-category["usage_units"], category["label"]))

    active_users = [user for user in users if user["activity_count"] > 0]
    most_consistent = max(
        active_users,
        key=lambda user: (user["active_days"], user["activity_count"], user["usage_units"]),
        default=None,
    )
    top_user_count = min(4, len(active_users))
    top_user_usage_units = sum(user["usage_units"] for user in active_users[:top_user_count])
    day_one_only_user_count = sum(
        1
        for user in active_users
        if {session["date"] for session in dated_by_user[PilotUserId(user["user_id"])]}
        == {pilot_start.isoformat()}
    )

    category_counts_match = (
        sum(category["activity_count"] for category in categories) == activity_count
    )
    category_units_match = (
        sum(category["usage_units"] for category in categories) == usage_units
    )
    reconciliation: PilotReconciliation = {
        "counts_match": sum(user["activity_count"] for user in users) == activity_count,
        "units_match": sum(user["usage_units"] for user in users) == usage_units,
        "allocation_matches": allocated_units == report["allocated_units"],
        "category_counts_match": category_counts_match,
        "category_units_match": category_units_match,
    }
    if not all(reconciliation.values()):
        raise ValueError("computed report failed deterministic reconciliation")

    return {
        "schema_version": 2,
        "metric": dict(policy["metric"]),
        "report_title": policy["report_title"],
        "report": report,
        "headline": {
            "active_users": len(active_users),
            "participant_count": len(users),
            "activity_count": activity_count,
            "usage_units": usage_units,
            "active_days": sum(1 for row in daily_activities if row["activity_count"] > 0),
            "elapsed_days": elapsed_days,
            "allocated_units": allocated_units,
            "remaining_units": None if allocated_units is None else allocated_units - usage_units,
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
        "daily_activities": daily_activities,
        "categories": categories,
        "computed_highlights": {
            "top_user_count": top_user_count,
            "top_user_usage_share_percent": _rounded_share_percent(
                top_user_usage_units, usage_units
            ),
            "most_consistent_user_id": (
                most_consistent["user_id"] if most_consistent else None
            ),
            "most_consistent_active_days": (
                most_consistent["active_days"] if most_consistent else 0
            ),
            "inactive_user_count": len(users) - len(active_users),
            "day_one_only_user_count": day_one_only_user_count,
            "undated_activity_count": len(undated_activities),
            "undated_units": sum(session["usage_units"] for session in undated_activities),
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
