# Portability and scope

Six canonical workflows define sales procedures, with shared configuration,
evidence helpers and an optional pilot PDF pipeline. Generated pointers are
optional entrypoints; the canonical procedures work from any host that can read
the workspace and present review artifacts. Local tools need Python 3.9+ and a
private writable run directory. Provider reads and approved effects additionally
need configured adapters. No host, CRM, mail service or analytics provider is
installed or authenticated by this repository.

Configure identity, timezone, native object/field/status mappings, activity
direction, record URLs and readback capabilities in the existing policy and
adapter files. Logical Account/Opportunity/Contact/Task/Event names describe the
normalized interface; providers may call them companies, deals, people or other
names. Unsupported capabilities remain explicit gaps. Approval and independent
provider readback requirements apply on every host.

Review the example business settings before live use: stage order and criteria,
required fields, follow-up rules, call types, research topics, review cadence,
forecast buckets, targets, currency and revenue basis. Stages need not use S0-S5.
`cadence` uses weekdays 0=Monday through 6=Sunday; it selects report detail and
week boundaries and creates no schedule. Manual runs can explicitly select daily
or extended pipeline review.

For month-based fiscal quarters, set `forecast.fiscal_year_start_month`. For
retail or irregular calendars, set ascending ISO `quarter_boundaries` covering
the current and next quarter; those boundaries take precedence. Name forecast
target keys by quarter start date, not an ambiguous fiscal-year label. Normalize
Amount into `reporting.currency` only with a reviewed conversion source and date;
do not sum incompatible currencies or revenue measures.

Pilot analytics are optional and disabled until configured. The
[analytics contract](../workflows/revenue/references/pilot-usage-queries.md)
accepts stable scope and participant IDs, activities and a configured quantity.
No credit system, grant, AI model, organization UUID or paid-trial CRM type is
required. The PDF covers participant activity and one additive non-negative
metric per run; use the chat report for other permitted metrics and name gaps.
Its local pipeline assembles, computes, validates, renders and prints without
connector calls. Printing requires pypdf and installed Chromium. System fonts
are the default; optional local fonts are hash checked.

Coverage checks use paired current-run normalized receipts and pagination.
They verify represented scope, success and counts; they cannot authenticate
provider responses or reveal records hidden by permissions. Synthetic validation
does not prove live credentials, native mappings or successful business effects.
Verify real reads and separately authorized effects in each deployment.

## Existing deployment migration

The close workflow and its skill/command pointers are removed. Won-deal
fulfillment belongs to the deployment's business process. Remove local close
configuration and any externally installed close pointer or schedule.

Compare existing local policy/adapters with the examples; never overwrite private
configuration wholesale. Mail helper names now use `mail_`; normalize Task Direction from provider metadata,
and add reporting,
cadence, fiscal-calendar and pilot metric settings. Pilot normalized input/report
schema is version 2: regenerate it from the new analytics contract, preserve old
run evidence, and obtain review again when scope, measurements or prose change.
Old pilot rows must not be relabeled without unit conversion and reconciliation.
