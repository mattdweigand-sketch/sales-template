# Forecast assessment

This file owns the saved assessment contract for Forecast Weekly. Bind
`forecast-assessment.json` as `inputs.json`'s `sources.forecast_assessment`.
`runs.py validate` checks it automatically; there is no separate approval or
provider call. `forecast_math.py` continues to calculate the supplied rows.

## One assessment per current-quarter bucket

The top-level object has only `deals`, an array containing exactly one entry per
`population: current` row in `forecast-input.json`, including excluded deals.
Booked and next-quarter rows retain their existing source requirements and do
not belong in this assessment array. An empty current-quarter population uses
`{"deals": []}`; a missing file is not an empty successful assessment.

Each entry has exactly:

- `deal_id`: the matching forecast row's ID. The bucket remains owned by that
  row; do not maintain another editable copy here.
- `rationale`: why the evidence supports that bucket under the configured rules.
- `statements`: the source-backed statements below, including contrary timing
  and the newest substantive buyer evidence. Preserve superseded statements.
- `blockers`: open blockers, each with `summary`, `statement_ids`, `owner` and
  `due_date`. Owner and ISO due date may be null when unknown. `[]` means the
  complete relevant evidence was reviewed and no open blocker was identified;
  `null` means blockers were not established. Resolved blockers remain explained
  by statements and the rationale, rather than listed as open.
- `conflicts`: unresolved conflicts, each with `statement_ids` (at least two)
  and `reason`. Use `[]` only when no unresolved conflict remains. Resolved timing
  conflicts require the explicit revision links below, not simply deleting the
  older source or its contrary statement.

### Statements and source locations

Each statement has exactly these fields:

```json
{
  "id": "timing-1",
  "source_id": "buyer-message-1",
  "source_refs": ["raw/buyer-message.json"],
  "text_path": ["body_text"],
  "speaker": "buyer",
  "speaker_name": "Example Buyer",
  "occurred_at": "2026-09-23T14:00:00Z",
  "quote": "Our decision has moved to October 15. We cannot sign in September.",
  "kind": "decision",
  "date_start": "2026-10-15",
  "date_end": "2026-10-15",
  "supersedes": [],
  "revision_quote": null
}
```

`id` is unique within the deal. `source_id` is the actual message/record identity
or an explicitly labeled local source identity. `source_refs` contains exactly
one run-relative saved full-body file. For JSON, `text_path` traverses object
keys and zero-based array indices to the decoded full body. For a plain-text
full body use `[]`. Subjects, snippets and previews are not full bodies. Retain
native originals; a quote-only extract cannot replace the decisive full source.

`speaker` is buyer, seller or unknown. Attribute `speaker_name` and the
offset-aware `occurred_at` to the source, not the collection time. `quote` must
be an exact nonblank substring of the selected body. The checker verifies the
substring and path, not the speaker's identity or the quote's meaning.

`kind` is signature, decision, milestone or context. An evaluation, demo,
security-review or paperwork deadline is a milestone unless the buyer actually
names it as signature/decision timing. Context and seller statements do not
establish buyer timing.

`date_start` and `date_end` are inclusive ISO dates. A single date uses the same
value for both. An explicit "this quarter" can use that configured quarter's
first and last days. Do not manufacture a precise date from vague wording;
use null for both bounds when timing cannot be resolved. Retain the original
wording so the reviewer can check the interpretation.

### Explicit revisions

`supersedes` lists earlier statement IDs, within the same deal, whose timing the
buyer explicitly revises. A revision needs a strictly later buyer
signature/decision statement, resolved date bounds, and an exact
`revision_quote` from that same full body explaining the revision. Without
supersession, `revision_quote` is null. A newer unrelated message, seller date,
or milestone cannot retire a buyer deferral. Preserve the old statement and its
source even after a valid revision.

The checker validates chronology, IDs, source quotes and statement kinds. The
reviewer must confirm that the revision actually supersedes the cited timing;
an arbitrary quote with a revision link is not proof.

## Enforced readiness

The check derives timing from active (not superseded) buyer signature/decision
statements, using the configured quarter already bound to the forecast:

- Every active range wholly within the quarter, with overlapping dates for each
  event kind (signature or decision):
  `in_quarter`. This is necessary, not sufficient, for Commit/Upside. Apply the
  remaining configured bucket criteria during review.
- An active range starts at or beyond the quarter's exclusive end:
  `deferred`. Commit/Upside is rejected; an excluded bucket can be complete.
- Missing/unknown buyer timing, a range crossing the quarter boundary, a past
  quarter range, nonoverlapping active dates for the same event kind, or an explicitly listed conflict:
  needs input. A stage label or CRM CloseDate cannot fill that evidence gap.
- Distinct decision and signature dates are not inherently contradictory. A
  decision this quarter does not cancel an explicit signature deferral. Declared
  conflicts and contradictory dates for the same event still require resolution.
- Unknown blockers withhold Commit/Upside. Commit additionally requires every
  recorded open blocker to have a named owner and date.

Missing assessments, incorrect IDs, missing source bodies, altered quotes,
invalid revision links and contradictory buckets make `report_complete` and
`ready_for_effects` false. A well-formed partial report remains reviewable with
no effects. Do not present arithmetic calculated from unresolved buckets as a
complete forecast, gap or target path.

A proposed ForecastCategoryName update must match the configured category for
that record's assessed current-quarter Commit/Upside bucket. Excluded and
next-quarter rows cannot acquire a category-sync proposal through this workflow.

The assessment, referenced bodies and this contract are frozen in the existing
review snapshot. Changes require renewed review. These checks constrain the
recorded interpretation; they cannot detect omitted evidence, authenticate a
source, or replace the existing human review of the actual buyer statements.
