---
cadence: weekly
reads: _shared/policy.yaml (cadence, crm, forecast, identity, pipeline, reporting, tooling), _shared/rules.md, _shared/adapters.json, setup/adapters.md, references/
writes: exact approved CRM changes
next: CRM and chat carry business state
---

# forecast-weekly

Build a source-backed quarterly forecast and reviewed path to target.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | cadence, crm, forecast, identity, pipeline, reporting, tooling | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#approval`, `rules#write_protocol`, `rules#scheduled_runs` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Opening text, "Load / Skip", opening of "Process", "Refuse", "Outputs and readiness", "Human check"; numbered sections at matching steps below | Fiscal scope, evidence, calculations and effects |
| Collection reference | [Pipeline collection](../pipeline-review/references/collect.md) | "Linked CRM sources" only, scoped by the forecast procedure | Task/Event fields; no pipeline report or pilot branch |
| Reference | [forecast-assessment.md](references/forecast-assessment.md) | Full file at step 3 | Timing, contrary evidence and source reconciliation |
| Reference | [report-format.md](references/report-format.md) | Full file at step 5 | Fixed report sections and evidence display |
| Request | Current chat; `<run>/request.md` | Owner, fiscal quarter, amount basis and requested scope | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |

## Process

1. Start per `rules#run_start` and the procedure’s "1. Load policy"; resolve fiscal boundaries and target.
2. Collect per "2. Collect from CRM" and "3. Collect from Calendar and mail".
3. Review every deal per "4. Bucket" and the assessment checklist, preserving contrary evidence.
4. Compute per "5. Compute" using `forecast_math`; reconcile source IDs and amounts.
5. Run coverage and Audit checks, then report per "6. Report" and the report format.
6. Apply only exact approved CRM changes per "7. Apply" and `rules#write_protocol`.
7. Close per "8. Close", naming unresolved coverage and proposal outcomes.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 5 | Buckets beside source quotes, contrary evidence, arithmetic and exact CRM proposals | Review forecast meaning and approve individual record changes or skip |

## Audit

| Check | Pass Condition |
|---|---|
| Evidence, before step 5 | Every covered deal appears once; full source bodies support timing, blockers and any explicit revision |
| Arithmetic, before step 5 | IDs and amounts reconcile to the source census; unknown amounts/targets retain the procedure’s limits |
| Coverage, before step 5 | Actual checker results are shown; unresolved timing, contradictions or coverage remain explicitly incomplete |
| Sources, throughout | Only configured forecast sources; pilot facts enter as corrected CRM state, without analytics reads or loading pilot reports |
| Effects, before step 6 | Selected capability, exact approval, fresh read and independent readback satisfy `rules#write_protocol` |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Forecast report and assessments | `<run>/outputs/review.md` and chat | Report layout plus per-deal quotes, timing and contrary evidence |
| Calculation input | `<run>/forecast-input.json` | Reviewed population, amounts, currency and source references per "5. Compute" |
| Approved effects and receipts | Configured systems; readbacks in the external run | Exact approved payloads, preimages, provider results and independent readbacks |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
