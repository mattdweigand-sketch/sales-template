---
type: workflow
command: close
mode: write
---
# close

Review a signed opportunity's close and track approved downstream handoff effects.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm; provisioning and handoff only when configured.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Resolve one Opportunity and read its Account, line items, Contact Roles and configured signed-term fields. Require the exact signed-evidence type listed in policy.close.signature_evidence. A verbal commitment or sent order form is insufficient.
2. Compare the record with the signed agreement. Separate matching terms, supported corrections and missing evidence. Never alter signed terms to satisfy an existing CRM record or invent a missing value.
3. Select a configured close path in _shared/adapters.md. If the organization uses billing or provisioning prerequisites, name them and obtain their system evidence. An unconfigured path stops at the review; do not create a trial as a generic workaround.
4. Propose individual effects for stage/date, win notes and terms, Account fields, Contact Roles, any configured downstream handoff, and follow-up Tasks. Show exact destinations and message text for a handoff.
5. Apply approved effects in the dependency order stated in the proposal. Fresh-read first and read back each result. Never mark a stage verified from an accepted request alone.
6. Report downstream items as verified, pending, blocked or not applicable, with source references and a named owner for unresolved work. Billing cancellation, invoices and provisioning require their own system evidence. Do not reopen a verified close through this workflow.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Verify signature evidence, exact signed terms, dependency order and each proposed destination. Approval to change the CRM does not approve a separate message or provisioning action.
