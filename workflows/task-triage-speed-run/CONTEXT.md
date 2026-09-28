---
cadence: daily
reads: _shared/policy.yaml (crm, email_voice, followup, identity, pipeline, tooling), _shared/rules.md, _shared/adapters.json, setup/adapters.md, references/
writes: exact approved CRM changes and unsent email drafts
next: CRM and chat carry business state
---

# task-triage-speed-run

Review the current task queue in groups and apply only approved follow-through.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | crm, email_voice, followup, identity, pipeline, tooling | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#approval`, `rules#write_protocol`, `rules#contact_status` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Opening text, "Load / Skip", opening of "Process", "Refuse", "Outputs and readiness", "Human check"; numbered sections at matching steps below | Collection, grouping, drafts and effects |
| Reference | [crm-corrections.md](references/crm-corrections.md) | Full file only for the CRM corrections group | Allowed identity fixes and exact per-record approvals |
| Request | Current chat; `<run>/request.md` | Selected owner and due, overdue or undated task scope | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |

## Process

1. Start per `rules#run_start` and the procedure’s "1. Load policy".
2. Collect Tasks and selected-thread evidence per "2. Collect the run" and "3. Gather evidence".
3. Review relationship facts per `rules#contact_status`, then run `triage_check` per "4. Group".
4. Post the complete readout per "5. Full readout".
5. Walk one group stage per "6. Section walk"; load "7. Drafts" or "9. CRM corrections" only for that stage.
6. Apply approved rows per "8. Writes", preserving independent readback; repeat the group walk until handled or deferred.
7. Run `closeout_check` on fresh complete Tasks and close per "10. Close" and "Human check".

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 4 | Complete grouped readout with stable Task numbers | Whether to walk the sections |
| 5 | The current group’s exact changes or full draft batch | Which rows to approve, correct, skip or defer; draft and date maps stay separate |

## Audit

| Check | Pass Condition |
|---|---|
| Accounting, before steps 4 and 5 | `triage_check` accounts for every Task, including held/unknown rows; interpreted facts match saved sources |
| Drafts, before step 5 approval | Full prior outbound/inbound context is read; recipients and exact draft fields pass the helper’s conflict checks |
| Effects, before steps 5 and 6 | Selected effect configuration, exact approvals and fresh preimages satisfy `rules#write_protocol` |
| Readback, before moving dates | Draft creation is independently verified; a failed or uncertain draft withholds its related Task move |
| Closeout, before step 7 output | Fresh complete Task output was checked; every unresolved Task is named, with no fabricated completion |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Review and proposals | `<run>/outputs/review.md` and chat | Editable Markdown with exact labeled effects, evidence and gaps |
| Disposition input | `<run>/triage-input.json` | Reviewed Task facts and exact draft candidates per "4. Group" and "7. Drafts" |
| Approved effects and receipts | Configured systems; readbacks in the external run | Exact approved payloads, preimages, provider results and independent readbacks |
| Close summary | `<run>/outputs/review.md` and chat | Disposition counts, unresolved rows and No emails sent. |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
