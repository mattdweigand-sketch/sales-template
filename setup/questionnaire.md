# Setup questions

Ask only what the selected workflow needs; preserve answers in their owning files.

1. Which owner, timezone and internal domains define scope? → policy.identity.
2. Which host and CRM/mail/calendar capabilities are available? Map native fields, states, activity direction, pagination and independent readbacks → adapters.md.
3. What follow-up timing, suppression, voice, call types and research topics apply? → policy followup/email/call_prep/research sections.
4. What stage order, entry criteria and required/conditional fields does the business use? → policy.pipeline. Replace the example stages as a consistent set.
5. Which working days, extended review day and week start apply? → policy.cadence. No schedule is created automatically.
6. What fiscal calendar, quarter targets, forecast criteria, category mappings, currency and revenue basis apply? → policy.forecast and reporting. Targets use ISO quarter-start keys; record conversion evidence before combining currencies.

Review the deployment configuration and one synthetic run before live use.
