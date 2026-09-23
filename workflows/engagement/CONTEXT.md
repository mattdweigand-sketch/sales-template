# Engagement workflows

Generated from scripts/wrapper-contract.json; procedures live in the linked files.

One job: route the requested engagement task.

## Inputs
- Working: output/{run-id}/request.md and the scope and source references it names.
- Reference: one selected workflow below and its Load / Skip list.

## Process
Choose one row and follow [the run lifecycle](../run.md). Skip sibling procedures and unrelated records.

| Command | Contract | Job |
|---|---|---|
| `sales-call-prep` | [sales-call-prep.md](sales-call-prep.md) | Prepare a sourced brief for one sales call or a named calendar window. |
| `interaction-sync` | [interaction-sync.md](interaction-sync.md) | Turn one completed customer interaction into reviewed CRM updates and an unsent follow-up draft. |
| `task-triage-speed-run` | [task-triage-speed-run.md](task-triage-speed-run.md) | Review due CRM tasks, prepare contextual follow-ups, and apply approved changes. |

## Outputs
The chosen workflow defines output/{run-id}/01_review.md, any declared artifacts, and 02_result.json.

## Human check
Read the workflow's exact review criteria and record review in output/{run-id}/review.json.
