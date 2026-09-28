# sales, the workflows

Seven workflows in `workflows/`. They do not hand files to each other. CRM carries the state between them. Every external write is its own numbered or lettered proposal, approved in the thread per `rules#approval`, then read back per `rules#write_protocol`.

| Workflow | Job |
|---|---|
| `sales-call-prep` | Brief the seller before an external call. Read-only per `rules#read_only_skills`. |
| `interaction-sync` | Log one completed call as lettered CRM proposals and one unsent draft. |
| `pipeline-review` | Flag deals whose CRM record lags the evidence and propose the fix. Owns Closed Lost. |
| `task-triage-speed-run` | Clear the due, overdue, and undated Task queue in grouped approvals. |
| `forecast-weekly` | Bucket every in-quarter deal and rank the path to target. |
| `pilot-usage` | Report how one pilot is used, in chat or as a customer PDF built in the external run directory. |
| `close` | Mark one signed deal Closed Won and finish the downstream checklist. |

Handoffs are in each procedure's `next` header.

## Loading

- A run reads its own `procedure.md`, the `references/` and `scripts/` it names, and the `_shared/policy.yaml` blocks and `_shared/rules.md` anchors its `reads` header lists. Load a specifically linked cross-workflow reference only when needed; skip sibling procedures.
- Approved collateral stays in the external directory configured by `policy.email_voice.collateral_path`; attach it only where a procedure allows it and the seller approves. `pipeline-review`, `task-triage-speed-run`, and `forecast-weekly` never load it and draft no product wording.

## Cadence and state

Cadence is suggested metadata; no automation is installed by this template. Configure schedules only on request using setup/automations.md. The suggested `pipeline-review` runs on configured working days and adds a rollup on the extended-review day. `forecast-weekly` follows that review so it reads current records. Values live in `policy.cadence`; behavior is defined in `rules#scheduled_runs`.

Factory (stable, every run) is `_shared/` and `workflows/`. Product (new each run) never lands in this repo. Proposals live in the thread, drafts in the configured mail service, records in CRM, PDFs in the external run directory. Status of a run is read from those places, never from files here.

The repository Codex skill of the same name is frontmatter plus a pointer to `procedure.md` and stops if the file is missing. Procedure frontmatter carries `cadence`, `reads`, `writes`, `next`.
