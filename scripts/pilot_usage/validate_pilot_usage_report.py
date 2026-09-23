#!/usr/bin/env python3
"""Validate a computed pilot report by recomputing every deterministic field.

Usage:
    python validate_pilot_usage_report.py --input input.json --policy _shared/policy.json --report report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from compute_pilot_usage_report import (
    PilotUsageInput,
    PilotUsagePolicy,
    PilotUsageReport,
    compute_pilot_usage_report,
)
from pilot_usage_policy import load_pilot_usage_policy


def validate_computed_pilot_usage_report(
    normalized_input: PilotUsageInput,
    policy: PilotUsagePolicy,
    computed_report: PilotUsageReport,
) -> list[str]:
    """Return exact validation failures; an empty list is safe to render."""
    problems: list[str] = []
    try:
        expected_report = compute_pilot_usage_report(normalized_input, policy)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"input_or_policy_invalid:{exc}"]
    if computed_report != expected_report:
        problems.append("computed_report_differs_from_recomputed_report")
    reconciliation = computed_report.get("reconciliation", {})
    for key in (
        "tasks_match",
        "credits_match",
        "grants_match",
        "category_tasks_match",
        "category_credits_match",
    ):
        if reconciliation.get(key) is not True:
            problems.append(f"reconciliation_failed:{key}")
    if computed_report.get("schema_version") != 1:
        problems.append("unsupported_report_schema_version")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recompute and validate a pilot usage report before rendering."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    normalized_input = cast(
        PilotUsageInput, json.loads(args.input.read_text(encoding="utf-8"))
    )
    policy = cast(PilotUsagePolicy, load_pilot_usage_policy(args.policy))
    computed_report = cast(
        PilotUsageReport, json.loads(args.report.read_text(encoding="utf-8"))
    )
    problems = validate_computed_pilot_usage_report(
        normalized_input, policy, computed_report
    )
    result = {"valid": not problems, "problems": problems}
    print(json.dumps(result, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
