# Pipeline collection

Use the configured CRM/mail/calendar adapters. These are logical selection
requirements, not native query text. Save issued requests, raw responses and
paired normalized receipts under the selected run. Page every search completely.

## Owned-open snapshot

Retrieve every Opportunity owned by the selected user
with IsClosed=false, ordered by CloseDate. Include Id, OwnerId, IsClosed, Name,
StageName, Amount, CloseDate, NextSteps, LastActivityDate, ForecastCategoryName,
Type, Account.Name, AccountId, every field in policy.pipeline.required_fields
and each conditional field and condition key. Preserve the original count;
derive policy.pipeline.in_scope_stages locally. Do not hide test-looking rows.
## Linked CRM sources

For all in-scope Opportunity and Account IDs, retrieve:
- Tasks with a date, either open or within policy.pipeline.activity_days:
  Id, Subject, ActivityDate, Status, IsClosed, TaskSubtype, Direction, WhatId,
  AccountId and Who.Name. Undated Tasks belong to task triage. Direction comes
  from verified adapter metadata, never a universal subject-prefix rule.
- Events within the activity window or upcoming: Id, Subject, ActivityDate,
  StartDateTime, EndDateTime, WhatId and AccountId. An elapsed event does not
  prove attendance. Retain both timestamps for coverage and hygiene checks.
- Contacts on those Accounts: Id, Email and AccountId. Derive external domains
  from returned addresses; missing domains remain explicit gaps.
## Hygiene

Run `policy.tooling.scripts.hygiene_check <opps> --tasks <tasks>
--events <events> --today <local-date> --as-of <run-start> --policy _shared/policy.yaml`.
Use the computed action deadline, newest note, activity receipts and flags.
Review unresolved dates before proposing a change.
## Daily review

Request inbound mail since yesterday in the reporting timezone,
excluding policy.identity.internal_domains, with no account narrowing. Reduce
saved results using policy.tooling.scripts.mail_digest for navigation only. Search calendar by each
in-scope Account name or verified Contact email from yesterday through
policy.tooling.calendar_lookahead_days. Match returned senders/attendees to
verified account domains. Upcoming meetings do not establish new buyer activity.
## Extended review

Request inbound mail per in-scope Account domain since
policy.pipeline.activity_days ago, and calendar records across configured
lookback/lookahead windows. Retrieve provider-backed record change history since
the preceding configured extended review day (or the run's explicit comparison
date), including new deals, stage/date changes and closures. If history is
unavailable, label the delta unavailable; never infer it from present values.
## Read decisive evidence

Fully inspect each assessed deal's newest substantive
buyer message and any additional full message needed to support or qualify a
finding/proposal. A digest, subject or preview cannot establish timing, stage
evidence, outcomes or absence of blockers. Preserve full bodies in the run;
missing/truncated bodies are gaps. Work by account/batch rather than loading
every mailbox body into one context.
## Coverage

Run `policy.tooling.scripts.coverage_check --calls <run>/calls
--scope pipeline-daily --since <run-start> --policy _shared/policy.yaml` for daily
review, or `--scope pipeline` for extended review. Use its result in the
[report header](report-format.md). On exit 1, resolve missing
checks and rerun; if unresolved, label coverage incomplete and withhold affected
proposals. No claim of complete coverage without the successful receipts.

Cadence comes from policy.cadence or an explicit daily/extended selection in this
run. Native provider query syntax and pagination belong in adapters.md. Source
failures are gaps, not empty result sets. Do not silently drop failed sources.

## Pilot report identity

Only in extended mode when the user supplies a pilot report: resolve its target
Opportunity in the owned-open snapshot and confirm its stage is in
policy.pipeline.in_scope_stages before using that record's AccountId. An unknown
or excluded stage leaves the report informational/needs-input unless the user
explicitly changes the run scope; update the scope and coverage before proposing.
Through
the configured CRM adapter, read the Account's stable Id, display name and the
actual mapped fields that link the usage source identity to this CRM Account.
Save the issued request, original response and mapping evidence in the external run.
Never resolve this link by display-name similarity. A missing target, unavailable
required mapping or missing Account result is needs-input. These reads serve only
rules#pilot_handoff; run no analytics query and load no other workflow's files.
