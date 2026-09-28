# Forecast Weekly

Build an evidence-backed quarterly forecast and propose explicit CRM corrections.

Apply rules#scheduled_runs. Pilot findings arrive only through corrected CRM state;
do not load a pilot report or read analytics as part of this workflow.

## Load / Skip

Read setup/adapters.md and the private policy blocks below. Start per
rules#run_start. Follow rules#approval and rules#write_protocol for effects.
Read only this procedure and the references it names; skip unrelated workflows.
All record and field names here are normalized logical names, mapped through the
configured adapter. Missing capabilities block only dependent steps.

## Process

Answers one question: what will close this quarter, backed by evidence from every source. CRM is the record; when Calendar or mail is fresher, the fresh evidence decides the bucket and the record gets a proposal. Every in-scope deal is accounted for. Nothing is written without an approval in the thread.

### 1. Load policy

From `_shared/policy.yaml`, load identity, forecast, reporting, cadence, tooling and the pipeline scope/stage-entry/NextSteps rules. Load the relevant CRM/mail/calendar adapter sections; skip engagement and research policy. Record the scope and offset-aware run start in request.md. Resolve current/next quarter using policy.forecast.fiscal_year_start_month or quarter_boundaries in policy.identity.timezone, matching _shared/scripts/coverage_check.py:quarter_bounds. Use inclusive starts and exclusive ends. Resolve target by ISO quarter-start key in policy.forecast.targets, falling back to target_default; neither set means `target not set`, with no gap math.

### 2. Collect from CRM

- Booked: all owned deals in the adapter-mapped won state whose CloseDate falls in the configured current quarter; include Id, OwnerId, IsClosed=true, IsWon=true, Name, Amount, CloseDate and Account.Name. Save the exact inclusive start/exclusive end in the coverage receipt.
- Open snapshot: every owned Opportunity with IsClosed=false; include Id, OwnerId, IsClosed, Name, StageName, Amount, CloseDate, NextSteps, LastActivityDate, ForecastCategoryName, AccountId and Account.Name. Save this complete owned-open snapshot for coverage, then derive current-quarter and next-quarter rows locally from `CloseDate`.
- Next quarter: use the next-quarter rows from that snapshot. Rows in policy.pipeline.in_scope_stages with an Amount are pull-in scope; all rows feed the preview when within `policy.forecast.next_quarter_preview_days` of quarter end.
- Tasks and Events for the open rows: use only the linked CRM query requirements in [pipeline collection](../../pipeline-review/references/collect.md), scoped to all in-quarter deals and eligible next-quarter deals. Run `policy.tooling.scripts.hygiene_check <opps> --tasks <tasks> --events <events> --as-of <run-start> --policy _shared/policy.yaml`; use its Next line and newest stored-entry date, not its blank-field flags (this snapshot omits required fields). Do not execute the reference's daily/extended mail or report steps.
- Record counts. Every in-scope row appears once in step 4. A query that errors stops the run; quote the message.

### 3. Collect from Calendar and mail

For each deal in `policy.forecast.evidence_scope`:
- Contacts on the Account: Id, Name, Email, AccountId. Preserve the returned Id and AccountId in coverage receipts.
- Calendar: events with any Contact email or the Account name, `policy.tooling.calendar_lookback_days` back to `calendar_lookahead_days` ahead, one query term per search, paged until no `next_cursor`. Record held meetings and accepted upcoming ones.
- mail: inbound messages from every known external Contact domain since quarter start, then supplemental Contact-name search when empty (policy.forecast.mail_lookup). Retain complete domain-scope receipts and page to the explicit terminal cursor. Use `policy.tooling.scripts.mail_digest` for navigation only. Fully read each assessed deal's newest substantive buyer message and every additional message needed to support or qualify timing, order-form status and blockers. An older optimistic body does not replace newer evidence. Preserve these full-body artifacts; missing/truncated bodies are gaps, never proof of no blocker.
- `not checked` per `policy.tooling.not_checked_means`.

### 4. Bucket

Apply `policy.forecast.timing_guard` before the first-match bucket rules: a buyer's explicit signature/decision deferral beyond this quarter excludes the deal unless later evidence explicitly revises that timing. Unresolved conflicting timing needs input and cannot enter Commit/Upside; an unrelated newer message or stale CRM date does not override it. Then test `policy.forecast.buckets` against complete evidence. Name failed conditions and sources. A passed CRM CloseDate alone does not exclude a deal. Apply pull_in separately to next-quarter scope, and record CRM corrections only under `policy.forecast.crm_gaps`.

Read [the assessment checklist](forecast-assessment.md). Save a
source-backed assessment for every current-quarter deal, including excluded
ones. Preserve exact quotes, full-body source paths, timing ranges, blockers,
contrary evidence and any later explicit revision. Review this beside the bucket.

### 5. Compute

Save `forecast-input.json`, in the external run directory: `quarter_start`, `quarter_end`, decimal-string-or-null `target`, and `rows`. Each row has `deal_id`, `population` (booked/current/next), `bucket` (commit/upside/excluded for current; null otherwise), decimal-string-or-null `amount`, `currency`, the reviewed `revenue_basis` label, and run-relative `source_refs`. Include every covered population member once; manually reconcile the IDs and values against the source census before claiming readiness.

Run `policy.tooling.scripts.forecast_math <run>/forecast-input.json --policy _shared/policy.yaml`. Use its exact totals and selected IDs; format only after calculation using policy.reporting. The path sentence uses `path_total` and `path_buffer`, not the optional all-Upside buffer. Unknown booked/Commit amounts mean a known subtotal and unknown count, not a complete call; withhold dependent gap/path math. Unknown Upside leaves the path incomplete. Target absent suppresses gap/path/buffer; pull-ins stay separate. The helper checks arithmetic, not bucket truth or authority of the supplied evidence.

### 6. Report

Run `policy.tooling.scripts.coverage_check --calls <run>/calls --scope forecast --since <run-start> --policy _shared/policy.yaml`. Exit 1 means incomplete: resolve it or deliver an explicitly partial report and withhold affected effects under the shared approval rules. Read [the report format](report-format.md), which owns header order and section layout. Notes use the checker's newest valid stored-entry date across in-scope deals; no valid date means unknown. If before the configured business-week start, append `no notes written this week`. Include every pull-in candidate/noncandidate, next-quarter preview only in its policy window, and source-supported CRM/category proposals.

Save the actual report and exact proposals in the external run directory.
Reconcile the calculation row IDs and amounts against the complete source census;
confirm the configured target and fiscal boundaries. Arithmetic success cannot
establish bucket truth. Unresolved timing or contradictions make the affected
forecast claims and proposals incomplete, even when sums are valid.

Then wait. Every proposal is one record per approval. `skip` is an answer.

### 7. Apply

Run `.venv/bin/python _system/scripts/setup.py doctor --workflow forecast-weekly --effect crm.write`
before a CRM proposal and again before applying it.
Resolve reported gaps and verify actual tools per rules#write_protocol.

Fresh read before each write. Write `NextSteps` per `policy.pipeline.next_steps_format`. Readback with changed fields and record link. Report rejections with the CRM message and one corrected proposal.

### 8. Close

Counts: booked, per bucket, pull-ins, proposals applied. Scope and source coverage come from the step 6 script line, not from memory.

### Refuse

Changing StageName or Amount (route to `pipeline-review`). Marking deals won. Drafting or sending email. Inventing a target. Treating a seller-stated date as buyer-named. Querying sources outside policy.forecast.sources without a scope change.

## Outputs and readiness

Save the forecast, source gaps and exact CRM corrections in
`<run>/outputs/review.md`; show the report in chat. Complete coverage and
calculation checks before following the [shared rules](../../../_shared/rules.md).

## Human check

Review each bucket beside its supporting quote, contrary evidence, blockers and
any claimed timing revision. Confirm speaker attribution and that a milestone
was not interpreted as a signature date. Review amount basis, target and exact
CRM corrections through the existing approval gate before any effects.
