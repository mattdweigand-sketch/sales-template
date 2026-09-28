# Local helpers

Paths are owned by policy.tooling.scripts. Helpers check mechanics, not business
truth or approval. Inputs and outputs remain in the external run directory.

| Helper | Contract |
|---|---|
| coverage_check | --calls, --scope pipeline-daily/pipeline/forecast, --since, --policy; validates paired logical selections, IDs, paging, windows and scope; --json emits structured readiness |
| hygiene_check | Opportunity output plus --tasks, --events, --as-of and --policy; checks configured stages/fields, activity timing and next-step deadlines |
| mail_digest | Saved full-body mail envelopes; navigation only, with truncated previews |
| mail_contact_stats | Owner email, saved envelopes, --only addresses, --calls, --since, --policy; counts only sufficiently complete source-linked history and reviewed classifications |
| forecast_math | Reviewed input path and --policy; decimal arithmetic, currencies, revenue bases, unknown amounts and selected path; reconcile inputs against source census independently |
| forecast_notify | Explicit --calls, --since, --policy and process status; generates chat status only, never sends or schedules |
| closeout_check | Fresh complete normalized Task output and --as-of; checks unresolved due/overdue/undated tasks |
| triage_check | Reviewed disposition JSON and --policy; checks complete task accounting, required evidence, timing and unresolved dependencies |
| pilot_usage | Explicit --run, --review, --roster-query, --activity-query, --output and --policy; verifies receipts, unit/window/linkage, computes JSON/HTML and optional --pdf |

Coverage supports the configured fiscal-year start or explicit quarter boundaries.
Normalized field names are logical contracts, not provider API assumptions. See
[the adapter contract](../adapter-contract.md). All-history unanswered claims require
unbounded, complete relevant history and substantive-response classification.
