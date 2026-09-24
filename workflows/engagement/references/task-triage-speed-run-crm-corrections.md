# CRM corrections

Interaction Sync and Task Triage share the identity checks below. The later Task-edit rules apply only to Task Triage. Corrections fix the record supported by evidence; they do not manufacture pipeline.

## Shared identity reconciliation

- Tie the person, employer and email together with mail or a current first-party page, and verify the CRM Account ID. Co-attendance or another attendee's domain is insufficient. State the source in the proposal.
- Search Contacts by verified email and by given/family names. Search Leads where the provider has Leads; no Lead concept is different from unavailable Lead access. Retain the returned record type, ID and relevant identity/relationship fields; do not require Contact-only fields on Leads.
- Reuse a verified matching Contact. For a converted Lead, fetch and verify its returned Contact link. An unconverted Lead is not a Contact and does not gain a guessed AccountId: report manual reconciliation/conversion when a Contact is needed. No automatic conversion or duplicate Contact create.
- Multiple plausible matches, contradictory employment evidence or a missing required search block create/re-parent. A unique Contact on another Account needs current employment evidence and its own exact AccountId proposal. Preserve OwnerId; any explicitly requested owner transfer is a separate proposal with separate approval.
- For a new Contact, approve the exact create, verify the returned ID, then propose downstream links separately. No placeholder IDs.

## Procedure per record

1. Fresh read of the Task and any Contact involved.
2. Apply the shared identity checks before create/re-parent. For a Task pointing at the wrong person, the outreach in mail must name the actual recipient.
3. Show any existing-record mismatch; apply only the supported correction within this workflow's allowed fields.
4. Show the exact change: record ID, each field, current value, proposed value. For a create, list every field to be written and the Account ID. For a Task `Subject`, replace only the person's name and keep everything else byte for byte.
5. One record per approval. For a new Contact, approve the create, verify the returned ID, then propose the Task `WhoId` link as its own change.
6. Write once. Read back every changed field. Report `Verified in CRM` or pending.

## Fields

- Contact create: `FirstName`, `LastName`, `Email`, `Title`, `AccountId`, `OwnerId` (the current user unless approved otherwise).
- Contact update: `Email`, `Title`, `AccountId`. Prepend `policy.crm.note_prefix` plus a one-line reason to `Description`, keeping existing text.
- Task update: `WhoId`, `Subject` (name substitution only).

## Not corrections

Deleting, merging, changing Opportunity fields, changing Account fields, changing any financial field, or touching more than one record per approval. List these under `CRM corrections needed` and leave them.
