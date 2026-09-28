# Pipeline Review

Review opportunity hygiene and propose evidence-supported next-step and field updates.

Apply rules#scheduled_runs.

Apply rules#next_steps.

## Load / Skip

Read setup/adapters.md and the private policy blocks below. Start per
rules#run_start. Follow rules#approval and rules#write_protocol for effects.
Read only this procedure and the references it names; skip unrelated workflows.
All record and field names here are normalized logical names, mapped through the
configured adapter. Missing capabilities block only dependent steps.

## Process

One run, one list. Each run flags deals in policy.pipeline.in_scope_stages whose CRM record has fallen behind the evidence and proposes the fix. The extended review adds the rollup, the delta, and stage and close date proposals. CRM is the record. Writes happen only on an approval in this thread. If the deployment explicitly configures a schedule, each scheduled run prepares the same review and waits for approval. This repository creates no schedules.

### 1. Load policy

From `_shared/policy.yaml`, load identity, pipeline, reporting, cadence, tooling, crm.record_url and forecast fiscal-quarter settings. Load the relevant CRM/mail/calendar adapter sections; skip engagement and research policy. Record scope, mode and one offset-aware run start. Explicit daily/extended mode wins; otherwise use policy.cadence.extended_review_weekday in policy.identity.timezone. Weekdays are Monday=0 through Sunday=6; working_days does not create a schedule.

### 2. Collect

Read and execute [references/collect.md](collect.md). Save the query outputs and retain the original opportunity count.

### 3. Propose

Read [the report format](report-format.md) for the fixed layout and exceptions. Every run reviews in-scope deals with hygiene triggers and the open Tasks supporting their live actions. Include an evidence-supported Task correction even without a hygiene trigger, with an empty flags list; `task_gap` is an informational date comparison, not a creation decision. Deduplicate by Opportunity ID. Other reviewed deals are counted, not listed. Unknown stages are unresolved scope, not exclusions. For each candidate show an evidence-supported proposal or needs-input finding. Apply the pipeline NextSteps formats/review rules; every changed clause requires a source, with no inferred buyer intent.

In extended mode, add Rollup (stage/category and fiscal quarter versus later), provider-backed Delta since the previous extended review date, and Record proposals. CloseDate follows `close_date_basis`; forward StageName needs the target criterion or an applicable stage_rules line. Regression needs affirmative evidence that a necessary current-stage condition no longer holds and a supported destination. Missing older evidence or silence alone is needs-input. A request to reassess permits investigation, not regression or a write; an exact user-directed stage change is a separately attributed proposal basis. Closed Lost needs a stated buyer no or verified silence for closed_lost_silence_days with no upcoming Event; widen evidence if the configured collection window is shorter. Amount needs buyer-confirmed/user-supplied evidence. Task proposals follow [proposals](proposals.md#task-review) in every mode; a verified action, deadline and record linkage are required.

Build the reviewed run file and render it per [report format](report-format.md).
Wait for approval of the displayed numbered recommendations; `all` covers only
those recommendations. Extended commercial proposals use separate letters.
Walk unresolved questions one at a time per [proposals](proposals.md#questions).
No reply writes nothing; the next run re-proposes from current CRM state.

### Pilot report input

Only when the user supplies a report in extended mode, use the current Account read
from [Pilot report identity](collect.md#pilot-report-identity) and rules#pilot_handoff.
An accepted report can support a separately labeled Record proposal for its verified
Account and in-scope Opportunity, subject to the existing field/stage evidence criteria. It is not a hygiene
trigger; keep it separate from flagged-deal counts and deduplicate effects on a record.
A missing handoff field or identity conflict is needs-input. Daily mode lists the
report as held for an extended review, with no pilot-based proposal or extra source
read. No report grants approval or widens this workflow's analytics access.

### 4. Apply

Run `.venv/bin/python _system/scripts/setup.py doctor --workflow pipeline-review --effect crm.write`
before a CRM proposal and again before applying it.
Resolve reported gaps and verify actual tools per rules#write_protocol.

Fresh read before each write. Write only the displayed, approved changes to NextSteps per `next_steps_format`; preserve an unchanged current entry and do not add a history note when none was proposed. Read back each record and rerun `hygiene_check` with a fresh `--as-of` timestamp; MISSING or unresolved REVIEW next-step status fails verification. Report rejections with the CRM message and one corrected proposal.

### 5. Close

Record each attempted field and verified outcome in the reviewed run file. Render
`receipt --final`; do not handwrite completion totals. Report fully written records,
partial field changes, failures and unattempted effects. Preserve successful writes.
Reconcile scope counts to the original snapshot per the report format.

### Refuse

Drafting or sending email. Marking deals won. Deleting or merging records. Changing OwnerId. Any write without an approval in this thread.

## Outputs and readiness

Save the complete report and exact proposals in the external run directory and
show them in chat. Retain exact payloads, source references, approvals, fresh
preimages, provider results and independent readbacks. A read-only run has no
effects. Record applied, pending, failed and skipped proposals honestly; the shared
approval rules govern every change. No separate run-engine files are required.

## Human check

Review hygiene findings against their evidence and confirm that each numbered
proposal maps to the exact effect payload before approving changes.
