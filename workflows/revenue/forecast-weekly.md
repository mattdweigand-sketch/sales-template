# Forecast Weekly

Build an evidence-backed quarterly forecast and propose explicit CRM corrections.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Query sketches use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

Answers one question: what will close this quarter, backed by evidence from every source. CRM is the record; when Calendar or mail is fresher, the fresh evidence decides the bucket and the record gets a proposal. Every in-scope deal is accounted for. Nothing is written without an approval in the thread.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. In a hosted project, sync the reusable files first. Record the selected scope in the run request. Record the run start time as an ISO datetime for `coverage_check --calls <run>/calls --since`. Resolve the current quarter and target from `policy.forecast.targets`, falling back to `policy.forecast.target_default`. If neither is set, the report says `target not set` and skips gap math.

### 2. Collect from CRM

- Booked: `SELECT Id, Name, Amount, CloseDate, Account.Name FROM Opportunity WHERE OwnerId = '<userId>' AND StageName = 'Closed Won' AND CloseDate = THIS_QUARTER`.
- Open in quarter: collect one complete owned-open snapshot for coverage, then derive the in-quarter rows with the following fields. `SELECT Id, Name, StageName, Amount, CloseDate, NextSteps, LastActivityDate, ForecastCategoryName, AccountId, Account.Name FROM Opportunity WHERE OwnerId = '<userId>' AND IsClosed = false AND CloseDate = THIS_QUARTER`.
- Next quarter: same fields, `CloseDate = NEXT_QUARTER`. S2+ rows with an Amount are pull-in scope; all rows feed the preview when within `policy.forecast.next_quarter_preview_days` of quarter end.
- Tasks and Events for the open rows, the queries in [pipeline collection](references/pipeline-review-collect.md), scoped to all in-quarter deals and eligible next-quarter deals. Run `policy.tooling.scripts.hygiene_check <opps> --tasks <tasks> --events <events> --today <date>`; its lines are the source for the Next line and the newest note date. Do not re-derive them from the text. Use only those two outputs; the query above omits `policy.pipeline.required_fields`, so its `blank_field` lines are not evidence here.
- Record counts. Every in-scope row appears once in step 4. A query that errors stops the run; quote the message.

### 3. Collect from Calendar and mail

For each deal in `policy.forecast.evidence_scope`:
- Contacts on the Account: Name, Email.
- Calendar: events with any Contact email or the Account name, `policy.tooling.calendar_lookback_days` back to `calendar_lookahead_days` ahead, one query term per search, paged until no `next_cursor`. Record held meetings and accepted upcoming ones.
- mail: one search per Account, `from:@<account domain> after:<quarter start>`, then by Contact name when empty (`policy.forecast.gmail_lookup`). Page until no `next_cursor`. When the platform saves a result to a file, run `policy.tooling.scripts.gmail_digest` on it and read only its output. Record last buyer message date, timing statements, order form status, blockers.
- `not checked` per `policy.tooling.not_checked_means`.

### 4. Bucket

Test `policy.forecast.buckets` conditions directly against the combined evidence, first match wins. A passed CloseDate does not exclude a deal; `pipeline-review` owns the date fix. Name the failed condition and its source for excluded deals. Apply `policy.forecast.pull_in` to the window deals. Where Calendar or mail shows activity, a meeting, or a buyer date CRM lacks, record a CRM gap per `policy.forecast.crm_gaps`.

### 5. Compute

Booked = Closed Won Amount sum. Call = booked + commit. Upside = upside sum. Gap = target minus call. Buffer = max(0, call + upside - target). Confirm the configured currency and revenue basis before summing; unknown amounts stay explicit, never silently zero. Pull-ins are separate and never counted twice. Path to target per `policy.forecast.path_to_target`; if upside runs out first, say `Upside does not cover the gap by $<n>.`

### 6. Report

Run `policy.tooling.scripts.coverage_check --calls <run>/calls --scope forecast --since <run start>` first and paste its output as the first line. Exit 1 means the report is not ready; follow the script's instructions. Read [references/forecast-weekly-report-format.md](references/forecast-weekly-report-format.md). Line 2 is `Notes as of <newest history-line date across in-scope deals>`; if that date is before this Friday, append `no notes written this week`. Order: booked and calling with the evidence clause per commit deal; forecast call and gap; path to target; pull-in scope, every deal, candidate or not; not in the call with reasons and sources; next quarter preview when in window; asks from Deal Desk, Legal, Security, or leadership found in any source; CRM gap proposals; ForecastCategory sync proposals per `policy.forecast.crm_sync`.

Then wait. Every proposal is one record per approval. `skip` is an answer.

### 7. Apply

Fresh read before each write. Write `NextSteps` per `policy.pipeline.next_steps_format`. Readback with changed fields and record link. Report rejections with the CRM message and one corrected proposal.

### 8. Close

Counts: booked, per bucket, pull-ins, proposals applied. Scope and source coverage come from the step 6 script line, not from memory.

### Refuse

Changing StageName or Amount (route to `pipeline-review`). Closed Won (route to `close`). Drafting or sending email. Inventing a target. Treating a seller-stated date as buyer-named. Searching Slack.

## Outputs and readiness

Save the forecast, source gaps and exact CRM corrections in
`output/{run-id}/01_review.md`; show the report in chat. Complete coverage and
calculation checks before following the [run lifecycle](../run.md).

## Human check

Review the evidence behind each forecast bucket, amount basis, target and
proposed CRM correction before approving effects.
