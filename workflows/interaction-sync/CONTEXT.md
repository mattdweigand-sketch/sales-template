---
cadence: one-off
reads: _shared/policy.yaml (call_prep, crm, email_voice, followup, identity, interaction, pipeline, tooling), _shared/rules.md, setup/adapters.md, ../task-triage-speed-run/references/crm-corrections.md, references/procedure.md
writes: exact approved CRM changes and unsent email drafts
next: CRM and chat carry business state
---

# interaction-sync

Turn one completed call into reviewed changes and an unsent follow-up.

## Inputs

Paths beginning with `_shared/`, `setup/` or `_system/` resolve from the repo root.
`<run>` is the unique external directory returned by the run initializer.

| Source | File or location | Load |
|---|---|---|
| Request | Current chat; record scope in `<run>/request.md` | One meeting ID/date, participants and transcript or supplied notes. |
| Run | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run's identity and evidence only |
| Policy | `_shared/policy.yaml` | call_prep, crm, email_voice, followup, identity, interaction, pipeline, tooling |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and logical mappings |
| Shared rules | [rules](../../_shared/rules.md) | run_start and the anchors cited by the procedure |
| Instructions | [procedure](references/procedure.md) | Full procedure; linked references only when that step needs them |

## Process

1. Follow `rules#run_start` to check setup, confirm the request and initialize a run.
2. Execute [the procedure](references/procedure.md) in its stated order, loading only
   the evidence and references needed for the current step.
3. Present the editable review and its gaps. Apply only effects permitted by the
   procedure and the shared approval/write protocol; preserve independent readbacks.

## Outputs

| Artifact | Location | Ready when |
|---|---|---|
| Review | `<run>/outputs/review.md` and chat | Required procedure sections, evidence links and gaps are explicit |
| Evidence | `<run>/raw/`, `<run>/calls/` | Source capture and applicable checks pass, or limitations are labeled |

## Human check

Confirm the customer statements and each exact CRM or draft proposal. Record the reviewed version and any exact approvals in the chat and
`<run>/outputs/review.md`. Edits require review of the changed proposal. Output
presence is not approval or proof that an external effect succeeded.
