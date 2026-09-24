"""Check recorded forecast evidence and timing constraints, never interpret prose.

The workflow owns statement extraction and human meaning review. Exact quotes,
dates and revision links make those judgments inspectable; they do not prove
speaker identity, source authenticity, or that all relevant evidence was found.
"""
from datetime import date
import json

from coverage_check import stamp
from wrappers import safe_path


def fields(value, required, label):
    if not isinstance(value, dict) or set(value) != set(required.split()):
        raise ValueError(label + ": expected only " + required)


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ": nonblank text required")
    return value


def day(value):
    if not isinstance(value, str):
        raise ValueError("date must be an ISO date string")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must use YYYY-MM-DD")
    return parsed


def ids(value, known, label, minimum=0):
    if (not isinstance(value, list) or len(value) < minimum
            or any(not isinstance(v, str) for v in value)
            or len(value) != len(set(value)) or not set(value) <= set(known)):
        raise ValueError(label + ": expected unique known statement IDs")
    return value


def body(run, statement):
    refs = statement["source_refs"]
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("statement needs exactly one full-body source_ref")
    path = safe_path(run, text(refs[0], "source_ref"))
    value = path.read_text()
    route = statement["text_path"]
    if not isinstance(route, list):
        raise ValueError("text_path must be an array of JSON keys/indices")
    if path.suffix.lower() == ".json":
        value = json.loads(value)
        for key in route:
            if isinstance(value, dict) and isinstance(key, str):
                value = value[key]
            elif isinstance(value, list) and type(key) is int and 0 <= key < len(value):
                value = value[key]
            else:
                raise ValueError("text_path does not select a saved full body")
        if route and isinstance(route[-1], str) and route[-1].lower() in {"snippet", "subject", "preview"}:
            raise ValueError("a subject/snippet/preview is not a full-body source")
    elif route:
        raise ValueError("plain-text sources require text_path: []")
    return text(value, "selected full body")


def assess(deal, bucket, run, start, end):
    fields(deal, "deal_id rationale statements blockers conflicts", "assessment")
    text(deal["rationale"], "rationale")
    if not isinstance(deal["statements"], list):
        raise ValueError("statements must be an array, including when none are available")
    statements, times, dates = {}, {}, {}
    required = "id source_id source_refs text_path speaker speaker_name occurred_at quote kind date_start date_end supersedes revision_quote"
    for statement in deal["statements"]:
        fields(statement, required, "statement")
        sid = text(statement["id"], "statement id")
        if sid in statements:
            raise ValueError("duplicate statement id: " + sid)
        statements[sid] = statement
        text(statement["source_id"], "source_id")
        text(statement["speaker_name"], "speaker_name")
        if statement["speaker"] not in ("buyer", "seller", "unknown"):
            raise ValueError("speaker must be buyer, seller or unknown")
        if statement["kind"] not in ("signature", "decision", "milestone", "context"):
            raise ValueError("kind must distinguish signature/decision from milestone/context")
        times[sid] = stamp(statement["occurred_at"])
        content = body(run, statement)
        if text(statement["quote"], "quote") not in content:
            raise ValueError(sid + ": quote is not present in the saved full body")
        first, last = statement["date_start"], statement["date_end"]
        if first is None and last is None:
            dates[sid] = None
        else:
            first, last = day(first), day(last)
            if first > last:
                raise ValueError(sid + ": reversed timing range")
            dates[sid] = (first, last)
        revision = statement["revision_quote"]
        if statement["supersedes"]:
            if text(revision, "revision_quote") not in content:
                raise ValueError(sid + ": revision_quote is not present in the saved full body")
        elif revision is not None:
            raise ValueError(sid + ": revision_quote needs an explicit supersedes link")

    buyer_timing = {sid for sid, s in statements.items()
                    if s["speaker"] == "buyer" and s["kind"] in ("signature", "decision")}
    superseded = set()
    for sid, statement in statements.items():
        prior = ids(statement["supersedes"], statements, sid + " supersedes")
        for old in prior:
            if sid not in buyer_timing or old not in buyer_timing or dates[sid] is None or times[sid] <= times[old]:
                raise ValueError(sid + ": a revision needs later dated buyer signature/decision evidence")
        superseded.update(prior)

    if not isinstance(deal["conflicts"], list):
        raise ValueError("conflicts must list unresolved evidence conflicts")
    for conflict in deal["conflicts"]:
        fields(conflict, "statement_ids reason", "conflict")
        ids(conflict["statement_ids"], statements, "conflict", minimum=2)
        text(conflict["reason"], "conflict reason")

    blockers = deal["blockers"]
    if blockers is not None:
        if not isinstance(blockers, list):
            raise ValueError("blockers must list open blockers, or be null when unknown")
        for blocker in blockers:
            fields(blocker, "summary statement_ids owner due_date", "blocker")
            text(blocker["summary"], "blocker summary")
            ids(blocker["statement_ids"], statements, "blocker", minimum=1)
            if blocker["owner"] is not None:
                text(blocker["owner"], "blocker owner")
            if blocker["due_date"] is not None:
                day(blocker["due_date"])

    active = sorted(buyer_timing - superseded)
    ranges = [dates[sid] for sid in active if dates[sid] is not None]
    # A decision and its later signature are distinct events. Compare competing
    # dates for the same event kind; either event can still defer the deal.
    conflicting = False
    for kind in ("signature", "decision"):
        same_kind = [dates[sid] for sid in active if statements[sid]["kind"] == kind and dates[sid] is not None]
        if same_kind and max(r[0] for r in same_kind) > min(r[1] for r in same_kind):
            conflicting = True
    timing = "unknown"
    if deal["conflicts"] or conflicting:
        timing = "conflicting"
    elif any(r[0] >= end for r in ranges):
        timing = "deferred"
    elif active and len(ranges) == len(active):
        if all(start <= r[0] <= r[1] < end for r in ranges):
            timing = "in_quarter"
        else:
            timing = "unresolved_range"

    errors = []
    if timing in ("unknown", "conflicting", "unresolved_range"):
        errors.append("buyer signature/decision timing needs input: " + timing)
    if timing == "deferred" and bucket in ("commit", "upside"):
        errors.append("buyer deferral beyond the quarter forbids Commit/Upside")
    if bucket in ("commit", "upside") and blockers is None:
        errors.append("blocker assessment is unknown")
    if bucket == "commit" and blockers is not None and any(b["owner"] is None or b["due_date"] is None for b in blockers):
        errors.append("Commit has an open blocker without a named owner and date")
    return {"timing": timing, "active_statement_ids": active,
            "superseded_statement_ids": sorted(superseded), "errors": errors}


def evaluate(data, forecast, run):
    """Require exactly one assessment per current-quarter bucket, including excluded."""
    result = {"ready": False, "errors": [], "deals": [],
              "note": "Recorded constraints and exact quotes checked; interpretation still needs human review."}
    errors = result["errors"]
    try:
        fields(data, "deals", "forecast assessment")
        if not isinstance(data["deals"], list):
            raise ValueError("deals must be an array")
        start, end = day(forecast["quarter_start"]), day(forecast["quarter_end"])
        if start >= end:
            raise ValueError("quarter boundaries must be ordered")
        expected = {r["deal_id"]: r["bucket"] for r in forecast["rows"] if r["population"] == "current"}
        seen = set()
        for index, deal in enumerate(data["deals"]):
            label = "deals[%d]" % index
            try:
                if not isinstance(deal, dict):
                    raise ValueError("assessment must be an object")
                key = text(deal.get("deal_id"), "deal_id")
                label = key
                if key in seen or key not in expected:
                    raise ValueError("duplicate or non-current-quarter assessment")
                seen.add(key)
                checked = assess(deal, expected[key], run, start, end)
                result["deals"].append({"deal_id": key, "bucket": expected[key], **checked})
                errors += [key + ": " + e for e in checked["errors"]]
            except (KeyError, TypeError, ValueError, OSError) as exc:
                errors.append(label + ": " + str(exc))
        if seen != set(expected):
            errors.append("assessments must match every current-quarter forecast row")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append("forecast assessment: " + str(exc))
    result["ready"] = not errors
    return result
