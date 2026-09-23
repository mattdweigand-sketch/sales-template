# Pipeline Review

Review opportunity hygiene and propose evidence-supported next-step and field updates.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Query sketches use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

One run, one list. Each weekday the run flags S2+ deals whose CRM record has fallen behind the evidence and proposes the fix. Friday adds the rollup, the delta, and stage and close date proposals. CRM is the record. Writes happen only on an approval in this thread. If the deployment explicitly configures a schedule, each scheduled run prepares the same review and waits for approval. This repository creates no schedules.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. In a hosted project, sync the reusable files first. Record the selected scope in the run request. Record one run-start ISO datetime with the user's local timezone offset for `coverage_check --calls <run>/calls --since` and `hygiene_check --as-of`.

### 2. Collect

Read and execute [references/pipeline-review-collect.md](references/pipeline-review-collect.md). Save the query outputs and retain the original opportunity count.

### 3. Propose

Read [references/pipeline-review-report-format.md](references/pipeline-review-report-format.md) and fill its fixed template in the final chat answer. Use it unchanged for manual and configured scheduled runs, including its pre-posting checks. For each flagged deal in `policy.pipeline.in_scope_stages`, show either one numbered, evidence-supported change or a needs-input finding with no proposed write. Format new or revised next-step entries per `policy.pipeline.note_next_line`; handle history and existing entries per `policy.pipeline.note_history_line` and `next_steps_format`. Apply `next_steps_review` before date-based proposals. Every clause traces to CRM, mail, or Calendar evidence. No inferred buyer intent. Deals with no trigger are counted, not listed. S0 and S1 deals are counted with their Amount sum on the header line.

Friday, add three sections. Rollup: count and Amount by stage and ForecastCategory, this quarter versus later. Delta since the previous Friday from OpportunityFieldHistory: new, stage moves, CloseDate moves, closed. Per record: CloseDate move per `close_date_basis`; StageName forward when `stage_entry` for the target stage is in evidence, quoted, or a `stage_rules` line applies; backward when the current stage's criterion is not in evidence; Closed Lost only after `closed_lost_silence_days` of silence with no upcoming Event or a stated buyer no; Amount only from a buyer-confirmed or user-supplied figure. A follow-up Task only where `hygiene_check` reports `task_gap`, due the verified action deadline, Not Started, linked to Contact and Opportunity.

Then wait. Notes and field fills approve as one batch: `approve all`, `approve all except <Accounts>`, or `skip`. StageName, CloseDate, Amount, Closed Lost, and Task creates are one record per approval. No reply writes nothing; the next run re-proposes from current CRM state.

### 4. Apply

Fresh read before each write. Write only the displayed, approved changes to NextSteps per `next_steps_format`; preserve an unchanged current entry and do not add a history note when none was proposed. Read back each record and rerun `hygiene_check` with a fresh `--as-of` timestamp; MISSING or unresolved REVIEW next-step status fails verification. Report rejections with the CRM message and one corrected proposal.

### 5. Close

Counts: open, in scope, reviewed, flagged, proposed, written, skipped, not checked. Open must equal the step 2 count. Reconcile reviewed, skipped, and not checked to the in-scope count per the report format.

### Refuse

Drafting or sending email. Closed Won (`close`). Deleting or merging records. Changing OwnerId. Any write without an approval in this thread.

## Outputs and readiness

Save the deliverable and exact proposals in `output/{run-id}/01_review.md`; show the complete report in the final chat answer. Retain full write payloads under the run's effect IDs and map numbered proposals to those IDs. Declare every source receipt and proposed artifact in its `artifacts` list. A read-only run has no effects. Readiness requires the checks above and explicit source gaps; unsupported effects stay withheld. Record the actual conversation review in `review.json`, and applied, pending, failed, or skipped effects in `02_result.json` through the shared run lifecycle.

## Human check

Review the scope, evidence and exact payloads. Approval covers only the listed effects and revision. Fresh reads and independent provider readbacks are required for external effects.
