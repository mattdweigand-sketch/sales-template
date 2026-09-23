# CRM corrections

Read when the CRM corrections group of `task-triage-speed-run` has at least one candidate. Corrections fix the record the evidence points at. They never manufacture pipeline or bypass reconciliation.

## Evidence required

- The person, employer, and email tie together in mail (a sent or received message to that address) or on a current first-party page. State the source in the proposal line.
- For a Task pointing at the wrong person, the outreach in mail names the actual recipient.

## Procedure per record

1. Fresh read of the Task and any Contact involved.
2. Duplicate search before any create or re-parent:
   `SELECT Id, Name, Email, AccountId, Account.Name, OwnerId FROM Contact WHERE Email = '<email>' OR (FirstName = '<first>' AND LastName = '<last>')`
   and the same on `Lead`. A hit means update or link that record, never create a second.
3. If the only hit sits on a different Account, show it and propose an `AccountId` update with the employment evidence. Preserve `OwnerId` unless the seller approves a transfer in the same message.
4. Show the exact change: record ID, each field, current value, proposed value. For a create, list every field to be written and the Account ID. For a Task `Subject`, replace only the person's name and keep everything else byte for byte.
5. One record per approval. For a new Contact, approve the create, verify the returned ID, then propose the Task `WhoId` link as its own change.
6. Write once. Read back every changed field. Report `Verified in CRM` or pending.

## Fields

- Contact create: `FirstName`, `LastName`, `Email`, `Title`, `AccountId`, `OwnerId` (the current user unless approved otherwise).
- Contact update: `Email`, `Title`, `AccountId`. Prepend `policy.crm.note_prefix` plus a one-line reason to `Description`, keeping existing text.
- Task update: `WhoId`, `Subject` (name substitution only).

## Not corrections

Deleting, merging, changing Opportunity fields, changing Account fields, changing any financial field, or touching more than one record per approval. List these under `CRM corrections needed` and leave them.
