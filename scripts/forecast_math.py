#!/usr/bin/env python3
"""Calculate reviewed forecast rows; never infer buckets or access providers.

Input: quarter_start/end (ISO dates), target (decimal string or null), and rows.
Rows: deal_id, population (booked/current/next), bucket (commit/upside/excluded
for current, null otherwise), amount (decimal string or null), currency,
revenue_basis, source_refs. Source/population/target authority is checked by
runs.py against the bound collection; this module only validates and calculates.
"""
import argparse
import datetime as dt
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path


def _amount(value, label, errors):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(label + ": expected decimal string or null")
        return None
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0:
            raise ValueError()
        return number
    except (InvalidOperation, ValueError):
        errors.append(label + ": non-finite, negative or invalid amount requires review")
        return None


def _text_amount(value):
    if value is None:
        return None
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def calculate(data, policy):
    """Return JSON-safe totals, unknown counts and contextual errors."""
    errors = []
    result = {"errors": errors, "complete": False, "row_ids": [],
              "known_subtotals": {}, "totals": {}, "selected_ids": [],
              "unknown_counts": {k: 0 for k in ("booked", "commit", "upside", "excluded", "next")}}
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        errors.append("forecast: expected object with rows array")
        return result
    if set(data) - {"quarter_start", "quarter_end", "target", "rows"}:
        errors.append("forecast: unsupported input fields")
    try:
        start = dt.date.fromisoformat(data["quarter_start"])
        end = dt.date.fromisoformat(data["quarter_end"])
        if start >= end:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        errors.append("forecast: quarter_start/end must be ordered ISO dates")
    if "target" not in data:
        errors.append("forecast: target must be explicit, including null")
    target = _amount(data.get("target"), "target", errors)
    reporting = policy.get("reporting") if isinstance(policy, dict) else None
    currency = reporting.get("currency") if isinstance(reporting, dict) else None
    if not isinstance(currency, str) or not currency.strip():
        errors.append("policy.reporting.currency: expected nonempty string")
    groups = {k: [] for k in result["unknown_counts"]}
    seen, bases = set(), set()
    for index, row in enumerate(data["rows"]):
        label = "rows[%d]" % index
        if not isinstance(row, dict):
            errors.append(label + ": expected object")
            continue
        required = {"deal_id", "population", "bucket", "amount", "currency", "revenue_basis", "source_refs"}
        if set(row) != required:
            errors.append(label + ": expected only " + ", ".join(sorted(required)))
        deal_id = row.get("deal_id")
        if not isinstance(deal_id, str) or not deal_id.strip() or deal_id in seen:
            errors.append(label + ": missing or duplicate deal_id")
        else:
            seen.add(deal_id)
            result["row_ids"].append(deal_id)
        population, bucket = row.get("population"), row.get("bucket")
        if population == "current" and bucket in ("commit", "upside", "excluded"):
            group = bucket
        elif population in ("booked", "next") and "bucket" in row and bucket is None:
            group = population
        else:
            errors.append(label + ": unsupported population/bucket combination")
            continue
        if row.get("currency") != currency:
            errors.append(label + ": currency differs from reporting currency; reviewed conversion required")
        basis = row.get("revenue_basis")
        if not isinstance(basis, str) or not basis.strip():
            errors.append(label + ": revenue_basis must name the reviewed basis")
        else:
            bases.add(basis)
        refs = row.get("source_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs):
            errors.append(label + ": nonempty source_refs required")
        if "amount" not in row:
            errors.append(label + ": amount must be explicit, including null")
        amount = _amount(row.get("amount"), label + ".amount", errors)
        if amount is None:
            result["unknown_counts"][group] += 1
        else:
            groups[group].append((deal_id, amount))
    if len(bases) > 1:
        errors.append("forecast: incompatible revenue bases; reviewed normalization required")
    if errors:
        return result
    amounts = [amount for rows in groups.values() for _, amount in rows] + ([target] if target is not None else [])
    with localcontext() as context:
        context.prec = max([28] + [len(n.as_tuple().digits) + abs(n.as_tuple().exponent) + len(str(len(amounts))) + 4 for n in amounts])
        sums = {k: sum((n for _, n in rows), Decimal(0)) for k, rows in groups.items()}
        known_call = sums["booked"] + sums["commit"]
        result["known_subtotals"] = {k: _text_amount(v) for k, v in {"booked": sums["booked"], "commit": sums["commit"], "call": known_call, "upside": sums["upside"]}.items()}
        unknown = result["unknown_counts"]
        totals = {"booked": None if unknown["booked"] else sums["booked"],
                  "commit": None if unknown["commit"] else sums["commit"],
                  "call": None if unknown["booked"] or unknown["commit"] else known_call,
                  "upside": None if unknown["upside"] else sums["upside"],
                  "gap": None, "all_upside_buffer": None, "path_total": None,
                  "path_buffer": None, "uncovered_gap": None}
        if target is not None and totals["call"] is not None:
            totals["gap"] = target - known_call
            if not unknown["upside"]:
                selected_sum = Decimal(0)
                remaining = max(Decimal(0), totals["gap"])
                for deal_id, amount in sorted(groups["upside"], key=lambda pair: (-pair[1], pair[0])):
                    if selected_sum >= remaining:
                        break
                    result["selected_ids"].append(deal_id)
                    selected_sum += amount
                totals["path_total"] = known_call + selected_sum
                totals["path_buffer"] = max(Decimal(0), totals["path_total"] - target)
                totals["uncovered_gap"] = max(Decimal(0), target - totals["path_total"])
                totals["all_upside_buffer"] = max(Decimal(0), known_call + sums["upside"] - target)
        result["totals"] = {k: _text_amount(v) for k, v in totals.items()}
        result["complete"] = not any(unknown[k] for k in ("booked", "commit", "upside"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--policy", type=Path, default=Path("_shared/policy.json"))
    args = parser.parse_args()
    try:
        result = calculate(json.loads(args.input.read_text()), json.loads(args.policy.read_text()))
    except (OSError, ValueError) as exc:
        result = {"complete": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
