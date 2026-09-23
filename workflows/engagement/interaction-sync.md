---
type: workflow
command: interaction-sync
mode: write
---
# interaction-sync

Turn one completed customer interaction into reviewed CRM updates and an unsent follow-up draft.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, calendar, mail; transcripts optional.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Locate the interaction using the configured transcript adapter or user-supplied notes plus the calendar event. State when no recording exists. Record its stable meeting ID, date, attendees and source.
2. Extract attributed buyer facts, commitments, explicit dates, unresolved discovery questions, and commercial figures with their source. Booking forms and seat wishes do not establish an agreed amount.
3. Reconcile Contacts, Account, open Opportunities, Contact Roles and related open Tasks. Resolve multiple plausible Opportunities with the user. Check the configured call marker in existing call activity to avoid duplicates.
4. Propose separately numbered effects for the completed-call Task, evidence-supported Opportunity changes, follow-up Task, unsent email draft, missing Contacts or roles, and completion of Tasks actually satisfied by this call. Use the exact CRM field mapping from the configured adapter.
5. Preserve existing note history. A next step records the action, supported owner and explicit due date. Use the buyer's date when they own the action; otherwise use policy.followup.default_next_date_days. A pilot end date alone does not establish the close date.
6. Show exact recipients, subject, body and any proposed attachments. Suggest only available, permitted collateral. Apply and verify only the approved effects through the shared run contract. Hand a signed close to close; do not infer it from a verbal commitment.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Read the attributed facts, every current-to-proposed CRM value, and the exact email. Approve effects by ID; one approval never silently includes other records.
