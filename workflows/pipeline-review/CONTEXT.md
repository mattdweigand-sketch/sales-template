---
cadence: daily
reads: _shared/policy.yaml (cadence, crm, forecast, identity, pipeline, reporting, tooling), _shared/rules.md, _shared/adapters.json, setup/adapters.md, references/
writes: exact approved CRM changes
next: CRM and chat carry business state
---

# pipeline-review

Review daily or extended pipeline evidence and propose exact record corrections.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | cadence, crm, forecast, identity, pipeline, reporting, tooling | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#approval`, `rules#write_protocol`, `rules#next_steps`, `rules#scheduled_runs` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Opening text, "Load / Skip", opening of "Process", "Refuse", "Outputs and readiness", "Human check"; numbered sections at matching steps below; "Pilot report input" only when supplied | Mode, proposals and verification |
| Reference | [collect.md](references/collect.md) | Common items plus "Daily review" or "Extended review"; "Pilot report identity" only when supplied in extended mode | Required reads and mechanical coverage |
| Reference | [report-format.md](references/report-format.md) | "All modes", "Approval and display rules", "Daily layout", "Exceptions and counts"; "Extended additions" in extended mode | Report and count identities |
| Conditional rule | [rules](../../_shared/rules.md) | `rules#pilot_handoff`, supplied report in extended mode only | Bounded report acceptance |
| Request | Current chat; `<run>/request.md` | Owner, date and explicit or configured daily/extended mode | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |
| Supplied pilot report | Report/source supplied in this run | Only in extended mode, per `rules#pilot_handoff` | Pilot evidence for the verified Account |

## Process

1. Start per `rules#run_start` and the procedure’s "1. Load policy"; resolve the configured mode.
2. Collect per "2. Collect" and the selected collection branch; retain the original count.
3. Prepare the report and exact proposals per "3. Propose"; use "Pilot report input" only when a report is supplied.
4. Apply only approved effects per "4. Apply" and `rules#write_protocol`.
5. Reconcile counts and close per "5. Close", reporting every pending, failed and skipped proposal.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 3 | Report, evidence, needs-input items and exact effects | Approve the displayed batch or individual record proposals as the procedure defines |

## Audit

| Check | Pass Condition |
|---|---|
| Coverage, before step 3 output | Actual coverage results are included; unresolved gaps label the report incomplete and withhold affected proposals |
| Meaning, before step 3 | Every changed clause has a source; stage, date and activity claims satisfy the procedure and full evidence |
| Pilot input, before step 3 | Extended mode only; the conditional Account read and `rules#pilot_handoff` checks pass, otherwise needs-input |
| Effects, before steps 3 and 4 | Selected capability, exact approval and fresh-read requirements hold; no won-state or email action |
| Verification, before step 5 | Readbacks and fresh hygiene checks pass for written records; counts reconcile to the original snapshot |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Review and proposals | `<run>/outputs/review.md` and chat | Editable Markdown with exact labeled effects, evidence and gaps |
| Approved effects and receipts | Configured systems; readbacks in the external run | Exact approved payloads, preimages, provider results and independent readbacks |
| Pipeline report and close counts | `<run>/outputs/review.md` and chat | Selected report layout with actual coverage results |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
