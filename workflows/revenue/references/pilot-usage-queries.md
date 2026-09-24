# Pilot analytics collection

This contract describes data, not a SQL dialect or product schema. The configured
analytics adapter may use a database, API or reviewed export. Record the exact
native request, stable pilot scope, reporting timezone, window, terminal success
and every page alongside the normalized results. Never infer a scope from a name
match. Use safe provider parameters for IDs and dates.

## Scope and metrics

Resolve one verified `scope_id` and explicit `pilot_start`, `pilot_end` and
`data_through` dates. A scope can be an account, project, site, subscription or
other deployment-defined pilot boundary. Configure the activity grain and unit
in `policy.pilot_usage.metric`; describe how the adapter identifies one activity,
attributed participant and quantity. IDs are opaque strings, not UUIDs or emails.

Each activity belongs to one participant; aggregate duplicate source rows to that
grain before normalization and retain the reconciliation evidence. `quantity`
is a non-negative decimal in the configured unit (for example hours, transactions
or calls). For an activity-count metric use one per observed activity. Do not
turn missing measurements into zero. Use separate runs for incompatible units.

## PDF datasets

Write one `results.json` object with these keys:

| Dataset | Columns and meaning |
|---|---|
| `roster` | `user_id`; optional `email` and `display_name`. One row per in-scope participant, including inactive participants. |
| `activities` | `activity_id`, `user_id`, `date` (ISO date in the reporting timezone), `quantity` (decimal or decimal string), optional `activity_title`. One row per activity inside the reviewed window. |
| `allocations` (optional) | `quantity` in the same unit, `effective_at` (reporting-local ISO date/time), optional `voided_at`. Include the applicable pilot allocation changes effective through the report date. Omit this dataset when no allocation applies; an empty array means a verified zero allocation. |

Internal participants are excluded by roster `email` against
`policy.identity.internal_domains`, with their activities excluded by `user_id`.
When email is unavailable, the adapter must establish external scope through
other verified membership evidence. Never guess membership from an opaque ID.

The assembler quantizes each activity and each eligible allocation half up to
`metric.decimal_places`, then sums integer `usage_units`. Thus 1.25 hours at two
decimal places becomes 125 internal units; the report displays 1.25 hours. This
is fixed-precision arithmetic, with no currency conversion. Raw quantities and
native receipts remain available for review. `enforce_allocation_limit` controls
whether usage above an allocation stops the report. Allocation dates never
define the pilot start. An allocation is a cumulative allowance for this window;
expiring balances or refunds require adapter reconciliation, not guessed arithmetic.

## Optional report sections

For chat reports, request only the configured permitted metrics:

- Roster and activity: the datasets above; active participants have at least one
  activity. Compute last-seven-day and weekly counts in the reporting timezone.
- Feature mix: complete counts by deployment-defined feature label and grain.
  Describe the denominator; do not force Search, Chat, AI model or product enums.
- Reviewed use cases: up to `use_case_sample` recent activity descriptions. Retain
  source IDs, group into supported themes, and show only audience-permitted text.

A missing optional section is unavailable with its reason. PDF roster/activity
failures stop the build. With a required allocation limit, allocation failures
also stop the build. A failed configured query cannot be relabeled as absent.

## Optional saved-call import

`--results` is the provider-neutral entrypoint. `--tool-calls` accepts this
normalized columnar receipt interface when an adapter emits saved query pages:

- `input_<id>.json`: `arguments.dataset` is `roster`, `activities` or
  `allocations`; matching `output_<id>.json` contains `result.query_id`.
- Result pages use `result.query_id`, `status`, `columns` (objects with `name`),
  `rows` (arrays in column order), `page_index` (zero-based), `page_count` and
  `total_count`. Column names match the dataset contract. The first page carries
  column metadata. A single page may omit page fields; its row count is complete.
- `status` is `success` or `succeeded` only after provider terminal success.
  Pending/queued/running/submitted pages do not supply rows. Explicit errors,
  missing pages or count mismatches stop assembly even if some rows are present.
- Keep one selected query per dataset in a run. When multiple saved queries are
  present, the latest saved submission selects the query; a newer failed query
  never falls back to old successful rows. Native timestamps, scope filters and
  terminal evidence must still be reviewed; file times cannot prove freshness.

These are normalized receipts, not assumed native provider responses. Keep the
originals, pagination proof and scope mapping beside them. Local checks cannot
prove that a provider exposed every record or that normalization was faithful.
