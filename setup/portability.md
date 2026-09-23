# Portability and scope

This is an independently usable ICM template derived from the reviewed
sales project, with seven canonical workflows. It is a new portable
implementation, not a byte-for-byte export or a validated deployment of the
original system's private helpers.

Preserved: workflow ownership, evidence attribution, exact action review,
fresh reads, provider readback, no sending email, and external systems of record.
Added for ICM: local editable review artifacts scoped to a task-supplied run ID.
These do not introduce a customer ledger or replace provider state.

Configuration: private identities, domain/owner IDs, CRM field names, quotas,
product claims, source repositories, schedules and collateral are absent.
The setup owns their local replacements. Example configuration is ignored
only after being copied to its deployment path; examples themselves are tracked.

Pilot analytics and closing need adapters specific to the deploying organization. Call prep accepts a missing transcript or adoption adapter as an explicit gap. No warehouse SQL, private fonts, internal provisioning flow or commercial prices are copied.

The interaction-sync default-date reference is owned by policy.followup.default_next_date_days. Stage and forecast definitions are deliberately unset until setup.

Included checks cover repository structure, wrapper routes, local review
freshness and synthetic cases. They do not validate credentials, field mappings,
live provider writes, outreach meaning, or every original production helper.
Install and exercise required adapters before describing a deployment as operational.
