# Portability and scope

Five canonical workflows define sales procedures, with shared configuration
and local evidence helpers. Generated pointers are optional entrypoints;
the canonical procedures work from any host that can read
the workspace and present review artifacts. Local tools need Python 3.9+ and a
private writable run directory. Provider reads and approved effects additionally
need configured adapters. No host, CRM, mail service or calendar provider is
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

Coverage checks use paired current-run normalized receipts and pagination.
They verify represented scope, success and counts; they cannot authenticate
provider responses or reveal records hidden by permissions. Synthetic validation
does not prove live credentials, native mappings or successful business effects.
Verify real reads and separately authorized effects in each deployment.
Deploy the intact clean export described in [installation.md](installation.md),
including hidden pointers and the setup/test/example files used by its links and
checks. A saved pointer without those repository dependencies is incomplete.

## Existing deployment migration

The close workflow and its skill/command pointers are removed. Won-deal
fulfillment belongs to the deployment's business process. Remove local close
configuration and any externally installed close pointer or schedule.

Compare existing local policy/adapters with the examples; never overwrite private
configuration wholesale. Remove local configuration, external skill pointers and
schedules for capabilities absent from the current task router. Mail helper names
use `mail_`; normalize Task Direction from provider metadata and configure
reporting, cadence and fiscal-calendar settings. Preserve old run evidence and
obtain review again when scope, evidence or proposals change.

Existing runs without inputs.json remain inspectable but unvalidated. Bind their
actual source files and exact effects, rerun checks, and obtain review of the
changed proposal before continuing. Preserve pending provider evidence and
reconcile uncertain effects first. Do not invent receipts or overwrite local
policy/adapters with examples to make an old run pass.

For this revision, compare and add the two helper paths
`tooling.scripts.forecast_math` and `tooling.scripts.triage_check`, and the
`forecast.timing_guard` rule from the example policy. Use the new input shapes
in each workflow. Forecast source settings name crm/calendar/mail exactly once;
stage keys, nonnegative integer thresholds and reporting precision must be valid.
Legacy mail envelopes remain readable for inspection, but definitive counts need
real paired receipts and reviewed classifications. Never synthesize completion.
