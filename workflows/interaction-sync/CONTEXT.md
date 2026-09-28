---
cadence: one-off
reads: _shared/policy.yaml (call_prep, crm, email_voice, followup, identity, interaction, pipeline, tooling), _shared/rules.md, _shared/adapters.json, setup/adapters.md, ../task-triage-speed-run/references/crm-corrections.md, references/
writes: exact approved CRM changes and unsent email drafts
next: CRM and chat carry business state
---

# interaction-sync

Turn one completed call into exact reviewed changes and an unsent follow-up.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | call_prep, crm, email_voice, followup, identity, interaction, pipeline, tooling | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#approval`, `rules#write_protocol`, `rules#next_steps`, `rules#contact_status` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Opening text, "Load / Skip", opening of "Process", "Refuse", "Outputs and readiness", "Human check"; numbered sections at matching steps below; "Pilot finding" only when supplied | Call reconciliation, proposals and readback |
| Shared identity reference | [CRM corrections](../task-triage-speed-run/references/crm-corrections.md#shared-identity-reconciliation) | "Shared identity reconciliation" at step 3 only | Contact identity and duplicate checks |
| Conditional rule | [rules](../../_shared/rules.md) | `rules#pilot_handoff`, only for a supplied finding tied to this call | Accept report evidence without running another workflow |
| Request | Current chat; `<run>/request.md` | Meeting ID/date, participants and transcript or completion-confirming notes | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |
| Supplied pilot finding | Report/source supplied in this run | Only a finding tied to this completed call | Evidence accepted per `rules#pilot_handoff`, never approval |

## Process

1. Start per `rules#run_start` and the procedure’s "1. Load policy".
2. Find the completed interaction and extract attributed facts per "2. Find the interaction" and "3. Extract".
3. Reconcile identity, linked records and duplicates per "4. Reconcile" and the shared identity reference.
4. Prepare exact proposals per "5. Propose"; load "Pilot finding" only for a supplied finding tied to this call.
5. Apply only approved effects per "6. Apply" and `rules#write_protocol`.
6. Close per "7. Close", recording each applied, skipped, pending or rejected effect.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 4 | Customer statements and labeled CRM/draft payloads | Approve the exact record changes, recipients and follow-up text |

## Audit

| Check | Pass Condition |
|---|---|
| Identity, before step 4 | A stable interaction marker and verified Account/Contact links exist; ambiguous duplicates remain needs-input |
| Meaning, before step 4 | Claims quote full sources; figures meet configured evidence rules; scheduled events do not establish completion |
| Effects, before steps 4 and 5 | The selected effect passes doctor and actual-tool checks; approval binds only the displayed version |
| Dependencies, before step 5 | New links use verified returned IDs; stale or pending prerequisites withhold dependent effects |
| Readback, before step 6 | Each applied effect has independent readback; uncertain drafts remain pending, never silently retried |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Review and proposals | `<run>/outputs/review.md` and chat | Editable Markdown with exact labeled effects, evidence and gaps |
| Approved effects and receipts | Configured systems; readbacks in the external run | Exact approved payloads, preimages, provider results and independent readbacks |
| Unsent draft | Configured mail drafts | Exact reviewed recipients, subject, body and thread; never sent |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
