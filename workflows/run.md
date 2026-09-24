# Run contract

One run holds one task, its review and any approved effects. The numbered files
encode prepare → human review → apply/readback; workflow families have no order.

## Start and bind inputs

Read the selected workflow's Load / Skip list. Run
`python3 scripts/runs.py init RUN_ID COMMAND` with a fresh task-supplied ID.
Write the request and exact scope in `output/{run-id}/request.md`. For Interaction
Sync, also persist `interaction_id: namespace:stable-id` there (see its workflow).
Never select another run merely because its folder exists.

Fill `inputs.json`: `started_at` is the offset-aware collection start, `mode` is
`daily` or `extended` for Pipeline Review (null otherwise), `sources` maps the
following names to files/directories inside this run. `unavailable_sources` is a
list of `{"name":"source-name","reason":"concrete gap"}`. A missing source is
not an empty successful result. `effects` is the exact proposal list below.

| Workflow | Required sources |
|---|---|
| sales-call-prep | `selected_call`: JSON with call_id and source_refs |
| interaction-sync | `interaction`: transcript or user notes; `reconciliation`: JSON with people and source_refs |
| task-triage-speed-run | `tasks`: selected Task census; `triage`: assessed helper input; `calls`: paired receipts; `mail`: raw mail file/directory |
| pipeline-review | `opportunities`, `tasks`, `events`: normalized record arrays; `calls`: paired receipts |
| forecast-weekly | Pipeline sources plus `forecast`: assessed forecast_math input; `forecast_assessment`: source-backed current-quarter bucket assessments |

A reconciliation person has `status` (matched/proposed/unresolved) and source_refs;
include the actual email, employer, Account and Contact/Lead findings described
in the workflow. Unresolved identity withholds effects. User notes are accepted
as notes, never relabeled provider evidence.

Mail statistics in any workflow additionally require `mail` and `calls` sources.
Use [adapter receipts](../_shared/adapter-contract.md); triage binds its selected
Task census to `selected_tasks` receipts. Calculations are recomputed from these
files; saved pass flags are not evidence. Forecast populations and target must
match the receipts and configured quarter. Unknown amounts remain visible gaps.
Forecast assessments additionally bind exact buyer quotes, dates, contradictions
and explicit timing revisions through the
[assessment contract](revenue/references/forecast-assessment.md). Their source
files are frozen with the review. Recorded consistency is not semantic approval.

All paths stay inside the active run; absolute paths, traversal and symlinks are
rejected. JSON `source_refs`/`evidence_refs` identify saved evidence files relative
to the run. Inside paired receipts, references are relative to `calls` (a sibling
`../raw/file.json` is allowed). Source files and directory inventories are frozen
automatically. The review's `artifacts` frontmatter list names only additional
files; do not repeat inputs there. Do not bind the entire run directory.

## Prepare and review

Write `01_review.md` with scope/coverage, the actual deliverable or explicit gap
report, attributed findings, checks and unresolved work. Set `status: ready`
when it is ready for human inspection. Run `python3 scripts/runs.py validate RUN_ID`.
It reports `can_review`, `report_complete`, `ready_for_effects` and contextual
errors. Exit 1 means invalid/incomplete. A status flag or untouched starter cannot
pass. Local checks validate structure/calculations, not the truth of prose.

A well-formed partial report may be reviewed with no approved effects. Required
source failures withhold effects conservatively; continue useful read-only
findings. Resolve the gap or narrow and review the scope before proceeding.
Legacy runs without inputs.json remain inspectable but unvalidated; they gain
no eligibility or renewed approval automatically.

Show the review and exact inputs.json proposals to the user. Use one
`## Effect A1` heading per effect ID; these headings must match the input list.
The machine entry owns the payload. Display its exact values during review;
do not keep an independently edited second payload. Full retained history may
be linked behind a compact proposed-change display.

Only after actual review/authorization, record its real conversation reference:

`python3 scripts/runs.py record-review RUN_ID --reviewer NAME --approval-ref REFERENCE --effects A1`

Omit --effects for read-only/partial review. The command records approval; it
cannot obtain it. Hashes freeze the request, inputs, raw evidence, deliverables,
policy, contracts and selected helper dependencies. Changed bytes invalidate it.

## Exact effects

Each inputs.json entry contains `id`, `operation`, `destination`, `record_id`,
`preimage`, `payload`, `source_refs`. Operations are update/create/draft/local_config.
Destinations are the workflow's permitted logical CRM type, `mail`, or the exact
shared configuration path. Unsupported operations/fields, sends, deletes and
merges are rejected. Call Prep permits no external effects; Forecast cannot
change StageName or Amount. A create/draft uses record_id:null; never guess an ID.

For updates, preimage contains every relied-on field, including changed fields.
`absent_fields` distinguishes fields absent from the record from fields present
with null. Retain exact adapter-normalized text and original provider bytes.
A NextSteps payload additionally declares `history_operation`: prepend,
replace_legacy, insert_history or unchanged. The helper automatically verifies
retained text/order; Description prepends retain the exact prior suffix. Lossy
markup conversion requires a separately scoped full-field review.

Draft payload keys are exactly to, cc, bcc, subject, body, attachments, thread_id,
reply_to_message_id. Lists remain lists, including empty cc/bcc/attachments; null
reply identity is explicit. Attachments are run-relative file paths also listed
in source_refs, with bytes retained for review. Its preimage includes existing_draft_ids:[] backed by
a fresh provider check. Each draft remains unsent.

For an explicitly requested configuration replacement, operation=local_config,
destination is a declared `_shared/` input, payload is
`{"staged_file":"proposed-policy.json"}` and source_refs includes that file.
Add frontmatter `expected_after: {"A1":{"_shared/policy.json":"SHA-256"}}` with
its real staged-file hash. The exact preimage remains in the review snapshot.
This narrow exception also works in Call Prep and grants no external capability.

## Apply and recover

Run `python3 scripts/runs.py status RUN_ID`. Require a current review,
ready_for_effects:true and actual user authorization before each effect. Re-read
every relied-on preimage field; any changed value or absent/null difference needs
a revised proposal. Use configured host adapters, then independent provider
readback. Draft verification must precede its dependent Task date update. A
newly created record ID must be verified before proposing a separate linking
update. A failed prerequisite holds its dependent action.

Before calling the provider, atomically write `02_result.json` with the exact
review_snapshot, a summary, recorded_at and one row per approved ID. Rows have
id, status (pending/verified/failed/skipped), attempt_started_at,
preimage_reference, provider_reference, readback_reference and detail. Untouched
pending rows use attempt_started_at:null. Set it to the current timestamp
immediately before a call. A timestamped pending row means uncertain outcome:
reconcile provider state before retrying. Atomic local writes do not create a
provider transaction. Hosts may import runs.atomic_json(path, data) to save the
existing file safely; there is no new executor or journal.

Save apply receipts under `effect-evidence/`, outside frozen collection folders.
Normalized preimage receipts contain effect_id, record_id, observed_at, fields
and absent_fields. Provider receipts contain effect_id, operation, destination,
record_id (including verified created ID) and the issued payload. Independent
readback receipts contain effect_id, record_id, observed_at and fields. Reference
these files from the result row. The local status check compares them against
the frozen proposal. Retain native responses alongside them for human inspection;
normalization and hashes cannot authenticate a provider. Adding apply evidence
does not stale review; editing original evidence does.

A read-only result has effects:[], including a partial report whose
report_complete:false remains visible. Unresolved effects remain incomplete.
A changed approved configuration without a result is recovery_required; inspect
and reconcile, never replay blindly. Before replacing a completed review,
preserve its prior result as an additional declared artifact. Pending attempts
must be reconciled first; record-review refuses to overwrite their approval.

## Status and boundaries

State names remain draft, awaiting_human_review, review_stale, review_current,
recovery_required, result_stale, incomplete and completion_recorded. Every check
recomputes source/calculation readiness. review_current means matching bytes;
completion_recorded means complete local result records. Neither proves actual
authorization or provider success. Inspect the original conversation and evidence.
Customer data and run outputs stay local; do not copy them into the template.
