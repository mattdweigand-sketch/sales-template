# Setup interview

Ask only unanswered questions needed by the selected workflows. Reuse known answers
from the current session or private configuration; never turn example defaults into
assumptions about the organization.

| Ask | Owning setting |
|---|---|
| Which workflows are useful, and which systems or supplied exports can support them? | adapters capabilities; unavailable optional effects stay disabled |
| Company/product names, seller identity, verified owner ID/email, timezone, internal domains and note author? | policy company and identity |
| Which CRM? Map logical objects, fields, native states, types, errors, queries, URLs and independent readbacks. | adapters field_mappings/state_mappings; policy crm |
| Which mail/calendar tools? What are their paging, history, full-body, reply-draft and access limits? | adapters capabilities and data_contracts |
| Follow-up intervals, cooldowns, writing voice, approved collateral directory, call types and research scope? | policy followup, email_voice, call_prep, research |
| Stage names/order, entry criteria, required/conditional fields and close criteria? | policy pipeline; all stage references must agree |
| Reporting currency, revenue basis, fiscal-year start or explicit quarter boundaries, and actual targets? | policy reporting and forecast; absent target stays null |
| Working days, extended review day and week start? | policy cadence; schedules remain inactive |
| For pilots: source/export, account identity, roster/activity grain, timezone, unit and desired report branding? | policy pilot_usage and company; adapters usage.read |
| For close: signature evidence, actual term fields, paths and required downstream items? Are handoff or provisioning needed at all? | policy close; optional effects disabled by default |

Do not request credentials in chat or write them into the template. Connect through
the selected approved app/MCP credential mechanism. Inspect a bounded read to verify
each live mapping, and record limitations. Setup is not approval to make writes.

Replace example email/domain, owner ID, CRM URL, seller signature and note author.
Use that author consistently in CRM and pipeline note formats. For pilot reports,
replace company/product names and PDF author. Doctor validates selected policy
blocks, stage consistency, numeric/date settings and required helper paths; the
user still reviews business meaning, fiscal rules, targets and note conventions.
`adapters.mode` is the only deployment mode setting.

No product claims or collateral ship with this template. Leave
`email_voice.collateral_path` null, or set it to an existing absolute directory
outside the repository. Attach a file only when the user approves that file for
the specific draft. Keep customer material outside the template and review dated
marketing claims against current sources.
