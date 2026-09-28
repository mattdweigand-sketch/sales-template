# Report format

## All modes

`policy.tooling.scripts.pipeline_render` owns the exact report, question, receipt,
close and notification wording. This file owns content requirements. Correct the
reviewed input and render again; never edit the rendered output by hand. Post the
complete report in chat and save it to `<run>/outputs/review.md`.
Logical fields and record URLs come from the configured adapter and policy.

## Run file

Keep one editable `<run>/outputs/pipeline-review.json` per run. Leave the existing
`<run>/run.json` identity file intact. The helper docstring defines the input keys:
run identity/mode, original counts, candidate deals, numbered blocks, questions,
extended additions and write outcomes. Use `daily` or `extended`, not a hardcoded
weekday. Keep full effect payloads, source bytes and independent readbacks in the
same external run. The JSON records review status; it is not proof of approval.

Retain every issued label, including superseded options. Never recycle labels or
reuse an earlier run's approval. If the file is lost, reconstruct it from the
versions and approvals in chat before continuing. Evidence source IDs stay in the
run; use only returned source URLs in displayed evidence.

Run `pipeline_render.py` from the repository root with the configured policy and
explicit external paths. Its modes are:

- `report --run <review.json> --coverage <coverage.json>`: report and proposals.
- `question --run <review.json> --label Q1`: one question and its exact options.
- `receipt --run <review.json> --labels 1,Q1-a --final`: outcomes and closing summary.
- `notification --run <review.json> --coverage <coverage.json>`: chat status JSON.

Use `.venv/bin/python` and the path in policy.tooling.scripts.pipeline_render.

## Approval and display rules

Number only exact supported changes. Unknowns, contradictions and missing evidence
belong in questions or withheld items. A deal may have a clear recommendation and
an independent question; never include a change that depends on the unanswered part.
`all` covers the displayed numbered recommendations only, excluding letters and
question options. Follow [proposals](proposals.md) for Task review and question labels.

Current next steps preserve source text with HTML line breaks/entities made readable.
Recommended next steps show the exact new first entry; older history stays unchanged.
For any history exception, provide both `current_full` and `proposed_full`, identify
it and compare the entire approved field. Preserve the configured note format and
retained history. A field-only change has no invented next step.

Each effect identifies the record, logical field, current and proposed value.
Evidence supplies date, source, person when known and supported fact. Calendar
timestamps establish scheduling only; attendance requires evidence. Mail evidence
is the retrieved set, not proof of full history. A helper cannot verify its meaning.

## Exceptions and counts

Use the original owned-open snapshot. `in_scope = reviewed + skipped + not_checked`
with disjoint statuses. Flags count reviewed deals with actual hygiene triggers;
an independently reviewed Task or accepted pilot-report proposal can have no flag.
Do not invent a trigger to include it. The helper checks counts against saved coverage.

Save the final `coverage_check --json` result once and reuse it for the report and
notification. Its scope must match daily/extended mode. On gaps, show the actual
incomplete result and name affected withheld deals; those deals have no approvable
changes. Keep unresolved process steps explicit, even if source coverage passes.

Receipts reconcile every approved field against recorded results. Missing results
are not attempted. A record is fully written only when all approved fields succeeded;
partial field changes remain visible and must not be repeated. Status and totals in
header, receipt and close use the same reconciliation. A fresh rerun uses a new
external run and explicitly supersedes the earlier review in chat.

## Extended additions

Supply the reviewed Rollup, provider-backed Delta and separately labeled commercial
proposals. Categories and currency follow deployment configuration. Unknown amounts
or missing history stay explicit gaps; never invent zero or say no changes without
history evidence. Each letter names its Opportunity and exact changed record.
Pilot-report proposals retain the existing conditional identity and evidence rules.

## Notification

The helper emits JSON status for chat; it never sends, writes, or schedules anything.
Daily complete runs with no recommendations or open questions return `send: false`.
Extended runs always return a status: ready for approval, complete, or incomplete.
Use the same saved coverage result; no second coverage run just for notification.
Only include a real thread URL when available. Authorized schedules follow
[optional schedules](../../../setup/automations.md); a formatting failure is reported
as incomplete, never replaced by a freehand ready notification.
