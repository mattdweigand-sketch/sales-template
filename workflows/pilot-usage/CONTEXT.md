---
cadence: one-off
reads: _shared/policy.yaml (company, pilot_usage, identity, tooling), _shared/rules.md, _shared/adapters.json, references/, setup/adapters.md
writes: local reports only; no business-system writes
next: reports reach CRM only through rules#pilot_handoff
---

# pilot-usage

Report one scoped pilot from a configured source or supplied export, without business writes.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | company, pilot_usage, identity, tooling | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#read_only_skills`, `rules#pilot_handoff` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Numbered steps 1–6, at matching steps below | Scope, collection and report review |
| Reference | [data-contract.md](references/data-contract.md) | Full file at steps 1–3 | Identity, window, unit, grain and receipts |
| Reference | [report-format.md](references/report-format.md) | Full file at steps 3 and 5 | Review JSON, output content and handoff fields |
| Reference | [pdf-format.md](references/pdf-format.md) | Build command at step 4; PDF options and page inspection only in PDF mode | Calculation/HTML and optional reviewed PDF |
| Request | Current chat; `<run>/request.md` | Account/source identity, pilot window, data-through date and output mode | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |

## Process

1. Start per `rules#run_start`; resolve scope per procedure step 1 and the data contract.
2. Collect roster and activity per procedure step 2, preserving raw evidence and complete scoped receipts.
3. Review linkage, classification and limits per procedure step 3; prepare review JSON.
4. Compute JSON/HTML per procedure step 4 using the exact run, review and query IDs.
5. Present the calculated report per procedure step 5; pause for content approval only for the customer PDF branch.
6. After PDF approval, build and inspect every page; finish per procedure step 6 and the report handoff format.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 5 | Customer PDF content, scope, units and limitations | Approve or correct the content before PDF generation |

## Audit

| Check | Pass Condition |
|---|---|
| Scope, before step 4 | Account/window/unit and source identity are verified; errors are not treated as empty data |
| Metrics, before step 5 | `pilot_usage` passes receipt, duplicate, user-linkage, unit/window and exact-quantity checks |
| Meaning, before step 5 | Interpretations cite records; activity does not establish completed work, realized ROI or customer approval |
| PDF, before sharing | Approved content and every rendered page pass visual inspection; failed candidates do not replace prior reports |
| Handoff, before step 6 output | Report companion carries `rules#pilot_handoff` fields or explicitly labels missing linkage; no business writes or delivery claim |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Usage review and handoff companion | `<run>/outputs/review.md` and chat | Reviewed observations, sources, scope, unit/grain and identity limits |
| Reviewed input | `<run>/review.json` | Review JSON per report-format.md |
| Usage artifacts | Explicit paths under `<run>/outputs/` | Helper JSON/HTML and optional reviewed, inspected PDF |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
