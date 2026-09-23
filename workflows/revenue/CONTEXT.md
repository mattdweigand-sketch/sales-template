# Revenue workflows

Generated from scripts/wrapper-contract.json; procedures live in the linked files.

One job: route the requested revenue task.

## Inputs
- Working: output/{run-id}/request.md and the scope and source references it names.
- Reference: one selected workflow below and its Load / Skip list.

## Process
Choose one row and follow [the run lifecycle](../run.md). Skip sibling procedures and unrelated records.

| Command | Contract | Job |
|---|---|---|
| `pipeline-review` | [pipeline-review.md](pipeline-review.md) | Review opportunity hygiene and propose evidence-supported next-step and field updates. |
| `forecast-weekly` | [forecast-weekly.md](forecast-weekly.md) | Build an evidence-backed quarterly forecast and propose explicit CRM corrections. |
| `pilot-usage` | [pilot-usage.md](pilot-usage.md) | Summarize one pilot's adoption from a configured analytics source. |
| `close` | [close.md](close.md) | Review a signed opportunity's close and track approved downstream handoff effects. |

## Outputs
The chosen workflow defines output/{run-id}/01_review.md, any declared artifacts, and 02_result.json.

## Human check
Read the workflow's exact review criteria and record review in output/{run-id}/review.json.
