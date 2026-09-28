---
cadence: one-off
reads: _shared/policy.yaml (identity, crm, pipeline, close), _shared/rules.md, references/, setup/adapters.md
writes: exact approved CRM changes; optional configured handoff or provisioning only with separate approval
next: named owners follow pending downstream items
---

# Close a signed deal

One deal in; verified close changes and a clear downstream checklist out. The signed
agreement governs terms. No product, price book, billing platform or provisioning
flow is assumed. Follow rules#run_start, rules#evidence and rules#approval.

## 1. Resolve and collect

Resolve the named deal and account using the configured CRM adapter. Read the
logical fields in [fields](references/fields.md), their native mappings, current
line items and configured close validation rules. Missing required mappings block
the affected proposal. If more than one deal matches, ask which before continuing.

## 2. Establish signature and commercial terms

Quote signature evidence permitted by policy.close.signature_evidence. A verbal yes,
sent order form or planned date is not signature evidence. Establish the signature
date independently before changing a close date; never substitute today. Compare
actual agreement scope, amount, currency, dates and terms with the record. No list
prices, default discounts or annualization formulas ship in this template. Missing
terms need input; contradictory terms require an explicit correction proposal.

## 3. Select the configured path

Use [paths](references/paths.md). State the supporting fact for new business,
renewal, expansion or a paid pilot. These labels do not infer a technical account
structure, cancellation obligation, admin invitation or billing migration.
Load optional downstream contracts only for effects configured for this path.

## 4. Propose exact effects

Use separate labels for each record or externally visible effect:

- **A. Deal update:** mapped won state, evidenced signature date where applicable,
  approved term corrections, win notes and an onboarding next step. If already won,
  propose only remaining changes. Preserve note history per rules#next_steps.
- **B. Account/contact updates:** only sourced differences. Never guess system IDs,
  roles, employer links, billing contacts or dates from a deal's stage.
- **C. Follow-up task:** a named owner, action and due date for a pending downstream
  item. Check existing tasks before creating another one.
- **D. Optional handoff:** only when policy.close.handoff.enabled is true and the
  configured destination and recipients are verified. Search/read existing handoffs
  first; display exact text and recipients. No configured posting capability means
  provide a chat draft or manual task; never claim it was sent.
- **P. Optional provisioning:** disabled by default. Follow
  [the provisioning contract](references/provisioning.md), disclose every side effect
  and obtain separate approval. It is not an automatic prerequisite for closing.

Required downstream items come only from policy.close.required_downstream. If the
organization explicitly makes a verified item a close prerequisite, hold A until
that prerequisite is satisfied. Otherwise report it independently; never invent one.

## 5. Apply and verify

Run `.venv/bin/python scripts/setup.py doctor --workflow close --effect crm.write`
before a CRM proposal and again before applying it. For a handoff or provisioning
proposal, select `--effect handoff.post` or `--effect provisioning.execute` instead.
An unavailable optional capability does not block an independent CRM change.
Resolve reported gaps and verify actual tools per rules#write_protocol.

Apply per rules#write_protocol. Reconcile errors and unknown success before retrying.
Never reopen a verified won deal merely to retry a downstream action. Restoring a
CRM field does not undo a provisioned account, invitation, charge or message.

## 6. Report

Show the deal's actual state and date, each applied/skipped/pending proposal, and
every configured downstream item as verified, pending, blocked or not applicable.
Cite the system readback or named owner's response. Give an owner and next action
for each unresolved item. Missing integrations do not become completed checklist rows.

Closed Lost belongs to pipeline-review. Sending email, deleting/merging records and
unconfigured provisioning are outside this workflow.
