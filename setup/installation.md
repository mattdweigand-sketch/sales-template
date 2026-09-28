# Install and configure

Install Python 3.10+ before starting (3.12 is the locally validated baseline).
Run commands from the repository root. If `python3.12` is unavailable, replace it
in the version check and venv command with the absolute path to an installed Python 3.10+ executable.
Do not use an older system Python. Verify that executable with `--version` first:

```sh
python3.12 --version
python3.12 -m venv .venv
.venv/bin/python -m pip install -r _system/requirements.txt
.venv/bin/python _system/scripts/setup.py init
.venv/bin/python _system/scripts/check_repo.py
.venv/bin/python -m unittest discover -s _system/tests -v
```

Use `.venv/bin/python` for every later command, including policy helper paths.
Activation is unnecessary and may not persist between Codex tool calls. From a
different working directory, use the absolute repo/interpreter paths or change to
the repo root first. For an existing workspace, read [migration](migration.md).

Initialization creates ignored `_shared/policy.yaml` and `_shared/adapters.json`
without overwriting existing files. Ask Codex to set up the selected workflow; it
follows [the questionnaire](questionnaire.md). Examples contain fictional identity,
neutral stages, no targets and no live services. Review the defaults and mappings.

Record the policy hash from `.venv/bin/python _system/scripts/setup.py policy-hash` in adapters.json only
after review. Mark configured capabilities with actual tools, contracts and verification
dates. Configure native CRM fields/states for workflows that need CRM. Run:

```sh
.venv/bin/python _system/scripts/setup.py doctor --workflow sales-call-prep
.venv/bin/python _system/scripts/setup.py requirements --workflow close --effect crm.write
.venv/bin/python _system/scripts/setup.py doctor --workflow close --effect crm.write
.venv/bin/python _system/scripts/run.py init sales-call-prep
```

Doctor checks configuration, never live access or business approval. It returns
exit 1 for missing settings. Use only the selected workflow's dependencies;
missing optional integrations are disclosed and their effects withheld. No remote,
connector, schedule or customer-system write is installed automatically.
Use repeated `--effect` flags for a proposal requiring multiple effects.
`--effects` checks all routine writes and every enabled optional close effect;
it is useful for a full deployment check, not for gating an unrelated action.

Open the repository as a Codex project and choose a skill in `/`, or explicitly
invoke `$sales-call-prep` and the corresponding names. Seven small pointers remain
in `.agents/skills`; their linked procedures own behavior. If they do not appear,
start a new chat in this project and check enabled skills. Do not copy only pointers
to a global skill folder, since their relative dependencies need this repository.

Configure approved apps or MCP tools privately. A project `.codex/config.toml` is
ignored; no endpoint or credential is supplied. [Adapters](adapters.md) defines
how to normalize provider data or supplied exports without inventing completeness.

Runs use unique external directories (default local application data, or `--base`).
Keep customer records, original exports and reports there, not in source control.
Pilot HTML/JSON needs no browser; optional PDF printing supports local Chromium and
macOS Chrome/Edge with system fonts. No vendor font downloads are required.
Inspect all rendered PDF pages before sharing. Configure retention for local data.

For redistribution use `git archive` after validation and commit. Verify the exported
files: seven pointer skills must be included; private configuration, caches, run
outputs and credentials must be absent. An archive excludes Git history; separately
review repository history before publishing an existing checkout.
