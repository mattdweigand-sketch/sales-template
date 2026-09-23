---
type: workflow
command: pipeline-review
mode: write
---
# pipeline-review

Review opportunity hygiene and propose evidence-supported next-step and field updates.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, mail, calendar.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Read open Opportunities within the user's scope and retain the total. Use policy.pipeline.in_scope_stages, mapped by the CRM adapter, for hygiene. Read stage-required fields, Tasks and timestamped Events.
2. Read buyer email and calendar evidence per in-scope deal. Record a coverage row for every deal and source, including missing access, paging limits and tool failures. Never describe an unchecked deal as checked.
3. Flag overdue next actions, new buyer activity, missing required fields, close-date risk or stale activity using configured rules. Distinguish the note's written date from the next action's due date. An ambiguous due date requires review, never guessed arithmetic.
4. Propose evidence-supported changes or a needs-input finding per flagged deal. Preserve dated history and the existing next action unless a replacement is proposed. A live next step is not stale merely because its note is old.
5. In the requested weekly mode, add stage and forecast-category totals, CRM field-history deltas, and separate stage, close-date, amount, loss and follow-up Task proposals. Do not claim a delta when field history is unavailable. A Task gap requires a known action deadline and no matching open Task.
6. Use configured stage criteria and buyer evidence. A pilot milestone alone cannot set a close date. Apply approved maps through the run contract, re-read results, and re-evaluate next-step validity. Reconcile open, in-scope, checked, flagged, proposed and unresolved counts.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Check coverage and the source behind each proposed clause. Approve exact note/field maps; stage, amount, close-date, loss and Task creation remain explicit record-level effects.
