# Generic pilot data

Configure the actual source and field mappings in the private usage.read adapter.
Source may be an analytics API, database or supplied file. Do not assume any SQL
schema, product mode, billing table, paid-seat definition or monetary conversion.

Use the shared paired receipt format with source `usage`, actual provider_query,
query_id, owner_id (the scoped operator/source identity), cursor and timezone.
Preserve raw data and errors. Results use status, records, total_count, next_cursor
and provider_reference. Follow native pagination to the explicit terminal page.

| Selection | Required descriptor | Rows |
|---|---|---|
| pilot_roster | account_id, as_of (data-through date), timezone | id (stable user ID), name; optional email |
| pilot_activity | account_id, start_date inclusive, end_date exclusive, timezone, unit | id (stable activity ID), user_id, date (ISO day), quantity (finite non-negative decimal string), unit; optional category |

Each row belongs to the scoped account by the actual source query or verified
file/export metadata. Human review must confirm that claim. A descriptor cannot
make an unrelated request scoped. For exports, retain original bytes and explain
how the account, date range, completeness and units were established.

Use a single normalized unit for each report. If conversion is needed, retain its
source and formula; never infer cost, credits, tokens or hours from another metric.
Dates use the configured timezone. One row is one recorded activity at the declared
grain; distinct days count only observed activity, not retention or completed work.
Unknown users, duplicate IDs, mixed units and out-of-window rows require correction.
Do not silently discard rows to make the check pass.
