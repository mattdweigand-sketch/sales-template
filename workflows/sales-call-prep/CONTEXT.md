---
cadence: one-off
reads: _shared/policy.yaml (call_prep, crm, identity, pipeline, research, tooling), _shared/rules.md, _shared/adapters.json, setup/adapters.md, references/
writes: nothing
next: CRM and chat carry business state
---

# sales-call-prep

Prepare a sourced brief for the selected calls, with explicit gaps and hypotheses.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | call_prep, crm, identity, pipeline, research, tooling | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#read_only_skills` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Opening text, "Load / Skip", opening of "Process", "Refuse", "Outputs and readiness", "Human check"; numbered sections at matching steps below | Collection and source boundaries |
| Reference | [brief-formats.md](references/brief-formats.md) | "All modes", then "Single call" or "Multi-call window" at step 5 | Selected brief layout |
| Request | Current chat; `<run>/request.md` | Selected calls, account/person identity and date window | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |

## Process

1. Start per `rules#run_start` and the procedure’s "1. Load policy".
2. Resolve calls per the procedure’s "2. Resolve the calls".
3. Collect per "3. CRM", "4. mail", "5. Prior calls" and "6. Public research", one source at a time.
4. Set call type and discovery gaps per "7. Call type and gaps".
5. Run the Audit checks, then write the selected brief per "8. Write the brief" and the brief format.

## Audit

| Check | Pass Condition |
|---|---|
| Sources, before step 5 | Every fact is sourced; inferences stay labeled Hypothesis; unread or incomplete sources are named |
| Coverage, before step 5 | Selected calls and discovery gaps are accounted for; limited mail history makes no never-replied claim |
| Scope, throughout | No business-system write; record issues appear only in CRM notes per `rules#read_only_skills` |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Call brief and CRM notes | `<run>/outputs/review.md` and chat | Selected brief format with evidence links, hypotheses and gaps |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
