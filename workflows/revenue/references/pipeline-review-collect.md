# Pipeline collection

Use the configured CRM/mail/calendar adapters. These are logical selection
requirements, not native query text. Save issued requests, raw responses and
paired normalized receipts under the selected run. Page every search completely.

1. **Owned-open snapshot.** Retrieve every Opportunity owned by the selected user
   with IsClosed=false, ordered by CloseDate. Include Id, OwnerId, IsClosed, Name,
   StageName, Amount, CloseDate, NextSteps, LastActivityDate, ForecastCategoryName,
   Type, Account.Name, AccountId, every field in policy.pipeline.required_fields
   and each conditional field and condition key. Preserve the original count;
   derive policy.pipeline.in_scope_stages locally. Do not hide test-looking rows.
2. **Linked CRM sources.** For all in-scope Opportunity and Account IDs, retrieve:
   - Tasks with a date, either open or within policy.pipeline.activity_days:
     Id, Subject, ActivityDate, Status, IsClosed, TaskSubtype, Direction, WhatId,
     AccountId and Who.Name. Undated Tasks belong to task triage. Direction comes
     from verified adapter metadata, never a universal subject-prefix rule.
   - Events within the activity window or upcoming: Id, Subject, ActivityDate,
     StartDateTime, EndDateTime, WhatId and AccountId. An elapsed event does not
     prove attendance. Retain both timestamps for coverage and hygiene checks.
   - Contacts on those Accounts: Id, Email and AccountId. Derive external domains
     from returned addresses; missing domains remain explicit gaps.
3. **Hygiene.** Run `policy.tooling.scripts.hygiene_check <opps> --tasks <tasks>
   --events <events> --today <local-date> --as-of <run-start> --policy _shared/policy.json`.
   Use the computed action deadline, newest note, activity receipts and flags.
   Review unresolved dates before proposing a change.
4. **Daily review.** Request inbound mail since yesterday in the reporting timezone,
   excluding policy.identity.internal_domains, with no account narrowing. Reduce
   saved results using policy.tooling.scripts.mail_digest. Search calendar by each
   in-scope Account name or verified Contact email from yesterday through
   policy.tooling.calendar_lookahead_days. Match returned senders/attendees to
   verified account domains. Upcoming meetings do not establish new buyer activity.
5. **Extended review.** Request inbound mail per in-scope Account domain since
   policy.pipeline.activity_days ago, and calendar records across configured
   lookback/lookahead windows. Retrieve provider-backed record change history since
   the preceding configured extended review day (or the run's explicit comparison
   date), including new deals, stage/date changes and closures. If history is
   unavailable, label the delta unavailable; never infer it from present values.
6. **Coverage.** Run `policy.tooling.scripts.coverage_check --calls <run>/calls
   --scope pipeline-daily --since <run-start> --policy _shared/policy.json` for daily
   review, or `--scope pipeline` for extended review. Use its result in the
   [report header](pipeline-review-report-format.md). On exit 1, resolve missing
   checks and rerun; if unresolved, label coverage incomplete and withhold affected
   proposals. No claim of complete coverage without the successful receipts.

Cadence comes from policy.cadence or an explicit daily/extended selection in this
run. Native provider query syntax and pagination belong in adapters.md. Source
failures are gaps, not empty result sets. Do not silently drop failed sources.
