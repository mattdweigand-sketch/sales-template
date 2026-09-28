# Upgrade an existing workspace

Keep a private backup outside this repository before upgrading. Older deployments
may use `_shared/policy.json`, `_shared/adapters.md` and `.claude/settings.local.json`.
These paths are ignored by Git and rejected if included in a public inventory.
Initialization reports them and preserves their bytes; it does not convert them,
activate tools or carry approvals forward.

1. Install the runtime in [installation](installation.md), then run
   `.venv/bin/python _system/scripts/setup.py init`. It creates only missing current files.
2. Inspect old private settings as configuration data. Review selected values with
   the user and transfer them into `_shared/policy.yaml` and version 2
   `_shared/adapters.json`. Do not copy old instructions, credentials, run state,
   provider assumptions or approval flags into the new template.
3. If a previous YAML file contains `mode`, remove that obsolete key after review.
   Use only `adapters.mode`. Reconcile the selected policy blocks with the current
   example; `requirements --workflow <name> --effect <capability>` lists the
   required field/state mappings and data-contract keys. Configure the actual
   available tools and repeat bounded read-only verification.
4. Review the current policy, record its hash and follow the setup doctor and
   rehearsal steps in [setup](CONTEXT.md). Changed policy requires a new review;
   neither old approvals nor a passing doctor authorizes a business write.
5. Retain or remove the old private files according to the user's retention needs.
   Do not delete their only copy as part of setup. If any private path was already
   tracked, ignoring it does not untrack it: remove that exact path from the Git
   index while preserving the local file, and review history before publication.
   Run the public checker and inspect a clean `git archive` before sharing.

The public template contains no organization-specific migration values. Setup is
complete only for the workflows and effects actually configured and verified.

## Repository layout update

Private configuration and external run locations are unchanged. Command names in
Codex are unchanged; regenerate their local pointers after a source update.

| Previous path | Current home |
|---|---|
| `scripts/` | `_system/scripts/` |
| `tests/` | `_system/tests/` |
| `requirements.txt` | `_system/requirements.txt` |
| Root provenance and validation documents | `_system/docs/` |
| `workflows/<name>/procedure.md` | `workflows/<name>/references/procedure.md`, entered through `workflows/<name>/CONTEXT.md` |

Update any external scripts, scheduled prompts or links that call the former paths.
The repository's commands, CI and pointers use the current paths. Local checks cannot
prove that an unlisted downstream consumer has been migrated.
