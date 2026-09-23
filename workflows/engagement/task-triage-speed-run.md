---
type: workflow
command: task-triage-speed-run
mode: write
---
# task-triage-speed-run

Review due CRM tasks, prepare contextual follow-ups, and apply approved changes.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, mail, calendar.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Query the current owner's open Tasks due today, overdue or undated, unless the user supplies a narrower scope. Retain the source count and resolve Contacts in batches. Missing records are correction findings.
2. Read recent sent and inbound email, existing drafts, and relevant calendar events. Distinguish substantive replies, out-of-office messages, bounces and calendar notifications. Before drafting, read the full most recent outbound message and any substantive reply.
3. Group each Task once: reply or meeting needs manual response; cold-contact recycle decision; hold due to recent mail, cooldown, unconfirmed recipient or channel; draft recommended. A substantive reply or meeting makes the Contact active. Active Contacts do not enter cold recycle logic.
4. Show the total and continuously numbered tasks, with the exact proposed action and reason. Reconcile the groups to the source count. A follow-up must continue a specific prior claim, offer or question in plain language.
5. Walk the groups on request. Present complete maps for bulk date moves or completions; draft approval is separate from moving the associated Task. Show each recycle's Contact and Task. Propose record corrections separately.
6. Before a write, re-read the affected record. A changed preimage is a conflict to re-propose. Preserve Description history, verify draft recipients and body, and verify every changed record. If quoted thread content includes an internal note, flag it for removal before the user sends.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Review each complete change map and exact draft. Approvals cover only named records and fields; failed rows do not authorize retries or unrelated changes.
