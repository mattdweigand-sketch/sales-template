# Set up this sales workspace

Use this process when the user says setup or when required configuration is absent.
Read [the questionnaire](questionnaire.md) and [installation](installation.md).
Ask only for unanswered items needed by the selected workflow. Existing answers
stay owned by private configuration; inspect them before asking again.

## Inputs

Selected workflows and known setup answers from the current chat;
`_shared/policy.yaml` and `_shared/adapters.json` when present; the questionnaire,
installation and provider guides linked here. Examples seed missing files only.

## Process

1. Complete runtime installation, then initialize local example files with
   `.venv/bin/python _system/scripts/setup.py init` from the repo root. If legacy settings
   are reported, follow [migration](migration.md); never inherit old approvals.
2. Collect identity, business policy and required adapter mappings. Edit only the
   private files; show a concise diff when changing an existing deployment. Use
   `.venv/bin/python _system/scripts/setup.py requirements --workflow <name>` to list the
   selected policy blocks, logical fields, states and data-contract keys. Include
   `--effect <capability>` when setting up a requested write capability.
3. Inspect the actual available connector schema and read access. Save non-secret
   mapping/verification notes in `_shared/adapters.json`. Credentials stay with the
   connector/MCP credential manager. Never put tokens in Git or chat.
4. Review policy with the user, record its SHA from `setup.py policy-hash` in the
   adapter configuration, and set `adapters.mode` to `configured` only when review
   is complete. There is no policy mode. Changed policy bytes require fresh review.
5. Run `.venv/bin/python _system/scripts/setup.py doctor --workflow <name>` for the selected
   read workflow and with `--effect <capability>` for each intended effect.
   Resolve every required gap; optional gaps withhold only the dependent action.
   Rehearse with synthetic evidence, then do
   a bounded read-only live check before offering a first exact write proposal.

## Outputs

Ignored `_shared/policy.yaml` and `_shared/adapters.json`; a setup summary
with configured capabilities, missing dependencies and validation limits.
No connector installation, external write, provisioning, message or schedule is
implied by setup. Use [adapters](adapters.md) for provider contracts and
[automations](automations.md) only when a schedule is explicitly requested.

## Human check

Review the selected policy and actual provider mappings before recording the policy
hash. Inspect remaining doctor gaps and the bounded read-only rehearsal. Setup
never approves effects or starts a schedule.
