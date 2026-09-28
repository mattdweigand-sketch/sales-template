---
cadence: one-off
reads: _shared/policy.yaml (identity, crm, pipeline, close), _shared/rules.md, _shared/adapters.json, references/, setup/adapters.md
writes: exact approved CRM changes; optional configured handoff or provisioning only with separate approval
next: named owners follow pending downstream items
---

# close

Review signed terms and exact close effects, with separately verified downstream outcomes.

## Inputs

Repository paths resolve from the root; `<run>` is the external run directory.

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | `_shared/policy.yaml` | identity, crm, pipeline, close | Configured values; examples are not deployment facts |
| Providers | `_shared/adapters.json`; [adapter guide](../../setup/adapters.md) | Selected capabilities and their logical mappings; guide when needed | Translate records and verify available tools |
| Shared rules | [rules](../../_shared/rules.md) | `rules#run_start`, `rules#evidence`, `rules#approval`, `rules#write_protocol`, `rules#next_steps` | Evidence, scope and applicable approval boundaries |
| Reference | [procedure.md](references/procedure.md) | Numbered sections at matching steps below | Signature, exact effects and outcome reporting |
| Reference | [fields.md](references/fields.md) | Full file at steps 2 and 3 | Configured logical fields and evidence requirements |
| Reference | [paths.md](references/paths.md) | Selected path at step 3 | Configured business path, without inferred technical effects |
| Reference | [provisioning.md](references/provisioning.md) | Full file only for configured provisioning or recovery after an attempt | Independent approval, verification and temporary-field restoration |
| Request | Current chat; `<run>/request.md` | One identified deal and signed agreement or verified signature evidence | Select this run |
| Run evidence | `<run>/run.json`, `<run>/raw/`, `<run>/calls/` | This run only; original bytes and paired receipts | Source identity, scope and provenance |

## Process

1. Start per `rules#run_start`.
2. Resolve and collect per "1. Resolve and collect" and the fields reference.
3. Establish signed terms and select the configured path per "2. Establish signature and commercial terms" and "3. Select the configured path".
4. Prepare exact effects per "4. Propose exact effects"; load provisioning only when that configured effect is relevant.
5. Apply approved effects per "5. Apply and verify" and `rules#write_protocol`; review restoration after any provisioning attempt.
6. Report actual state and downstream dispositions per "6. Report".

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 4 | Signed terms, current/new values, recipients and separately disclosed downstream effects | Approve each exact effect or skip; optional provisioning has its own approval |

## Audit

| Check | Pass Condition |
|---|---|
| Terms, before step 4 | Signature evidence and date are independently established; missing or contradictory terms remain needs-input |
| Configuration, before steps 4 and 5 | Only configured effects and prerequisites; the selected capability and actual tool checks pass |
| Dependencies, before step 5 | Required downstream prerequisites hold; existing task/handoff checks run and verified won state is never reopened |
| Recovery, after each provisioning attempt | Temporary fields are compared to preimages; necessary restoration is separately proposed, preserving concurrent changes |
| Outcome, before step 6 | Every claimed success has independent evidence; unresolved effects have an owner and next action |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Review and proposals | `<run>/outputs/review.md` and chat | Editable Markdown with exact labeled effects, evidence and gaps |
| Approved effects and receipts | Configured systems; readbacks in the external run | Exact approved payloads, preimages, provider results and independent readbacks |
| Downstream checklist | `<run>/outputs/review.md` and chat | Verified, pending, blocked or not applicable, with sources and owners |
| Evidence and receipts | `<run>/raw/`, `<run>/calls/` | Original source bytes and paired normalized JSON |
