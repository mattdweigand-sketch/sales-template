# Pipeline Review

Review opportunity hygiene and propose evidence-supported next-step and field updates.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), this procedure and the policy sections named below. In the [run lifecycle](../run.md), read Start/Prepare/Status for review; read Exact effects/Apply only when proposing or executing changes.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Collection requirements use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

One run, one list. Each run flags deals in policy.pipeline.in_scope_stages whose CRM record has fallen behind the evidence and proposes the fix. The extended review adds the rollup, the delta, and stage and close date proposals. CRM is the record. Writes happen only on an approval in this thread. If the deployment explicitly configures a schedule, each scheduled run prepares the same review and waits for approval. This repository creates no schedules.

### 1. Load policy

From `_shared/policy.json`, load identity, pipeline, reporting, cadence, tooling, crm.record_url and forecast fiscal-quarter settings. Load the relevant CRM/mail/calendar adapter sections; skip engagement and research policy. Record scope, mode and one offset-aware run start. Explicit daily/extended mode wins; otherwise use policy.cadence.extended_review_weekday in policy.identity.timezone. Weekdays are Monday=0 through Sunday=6; working_days does not create a schedule.

### 2. Collect

Read and execute [references/pipeline-review-collect.md](references/pipeline-review-collect.md). Save the query outputs and retain the original opportunity count.

### 3. Propose

Read [the report format](references/pipeline-review-report-format.md) for the fixed layout and exceptions. Daily candidates are in-scope deals with hygiene triggers. Extended candidates are their union with in-scope `task_gap` deals; the gap remains separate from hygiene triggers. Deduplicate by Opportunity ID. Other reviewed deals are counted, not listed. Unknown stages are unresolved scope, not exclusions. For each candidate show an evidence-supported proposal or needs-input finding. Gap-only Tasks belong in extended Record proposals. Apply the pipeline NextSteps formats/review rules; every changed clause requires a source, with no inferred buyer intent.

In extended mode, add Rollup (stage/category and fiscal quarter versus later), provider-backed Delta since the previous extended review date, and Record proposals. CloseDate follows `close_date_basis`; forward StageName needs the target criterion or an applicable stage_rules line. Regression needs affirmative evidence that a necessary current-stage condition no longer holds and a supported destination. Missing older evidence or silence alone is needs-input. A request to reassess permits investigation, not regression or a write; an exact user-directed stage change is a separately attributed proposal basis. Closed Lost needs a stated buyer no or verified silence for closed_lost_silence_days with no upcoming Event; widen evidence if the configured collection window is shorter. Amount needs buyer-confirmed/user-supplied evidence. A Task create requires task_gap, a verified action/deadline and record links; an unresolved date never supports it.

Then wait. Notes and field fills approve as one batch: `approve all`, `approve all except <Accounts>`, or `skip`. StageName, CloseDate, Amount, Closed Lost, and Task creates are one record per approval. No reply writes nothing; the next run re-proposes from current CRM state.

### 4. Apply

Fresh read before each write. Write only the displayed, approved changes to NextSteps per `next_steps_format`; preserve an unchanged current entry and do not add a history note when none was proposed. Read back each record and rerun `hygiene_check` with a fresh `--as-of` timestamp; MISSING or unresolved REVIEW next-step status fails verification. Report rejections with the CRM message and one corrected proposal.

### 5. Close

Counts: open, in scope, reviewed, flagged, proposed, written, skipped, not checked. Open must equal the step 2 count. Reconcile reviewed, skipped, and not checked to the in-scope count per the report format.

### Refuse

Drafting or sending email. Marking deals won. Deleting or merging records. Changing OwnerId. Any write without an approval in this thread.

## Outputs and readiness

Save the deliverable and exact proposals in `output/{run-id}/01_review.md`; show the complete report in the final chat answer. Retain full write payloads under the run's effect IDs and map numbered proposals to those IDs. Bind source files and exact proposals in inputs.json; use the review’s `artifacts` list only for additional deliverables. A read-only run has no effects. Readiness requires the checks above and explicit source gaps; unsupported effects stay withheld. Record the actual conversation review in `review.json`, and applied, pending, failed, or skipped effects in `02_result.json` through the shared run lifecycle.

## Human check

Review hygiene findings against their evidence and confirm that each numbered
proposal maps to the exact effect payload before approving changes.
