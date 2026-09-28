# Pilot usage

Prepare a usage report for one account and an agreed pilot window. Follow
rules#run_start, rules#evidence and rules#read_only_skills. Data may come from an
approved analytics adapter or a user-supplied export; no warehouse schema is assumed.

1. Resolve account, customer label, pilot start/end and data-through date. Confirm
   the unit, timezone and grain under policy.pilot_usage. Do not derive a pilot
   start from billing grants or equate money with usage. Missing scope needs input.
2. Follow [the data contract](data-contract.md). Collect a roster
   snapshot and the complete scoped activity records, preserving actual paging,
   raw evidence and normalized receipts. A failed source is not an empty dataset.
3. Review identity linkage, duplicates, classification and source limitations.
   Use neutral categories or explicitly reviewed activity-ID category overrides.
   Record the review JSON from [the report format](report-format.md).
   Narratives must cite source records; label potential value as potential. An
   activity log alone establishes neither completed work nor realized ROI.
4. Run policy.tooling.scripts.pilot_usage with the explicit run, review, roster query,
   activity query and output paths. The helper checks receipt binding, account/window,
   units, unique IDs and exact quantities. It never calls business systems.
5. Present the calculated report with scope and gaps. For a customer PDF, get review
   of its content per rules#approval, generate it via the same helper with --pdf,
   then render and inspect every page before sharing. Use [PDF guidance](pdf-format.md).
6. Report sources, window, unit and any missing data. A local PDF is not delivery;
   do not upload, post, send or update CRM from this workflow.
