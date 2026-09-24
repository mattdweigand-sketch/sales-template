# Installation

## Local agent
Keep the repository intact. Python 3.9+ runs local checks and evidence helpers.
Copy the factory examples once, preserving an existing configuration:

```bash
cp -n _shared/policy.example.json _shared/policy.json
cp -n _shared/adapters.example.md _shared/adapters.md
python3 scripts/check_repo.py
python3 -m unittest discover -s tests -v
```

Fill the [questionnaire](questionnaire.md). Keep mode example for synthetic
use; set mode live only after required adapters and workflow settings are
configured and reviewed. No command here installs a connector or creates
a schedule. Missing private adapters remain explicit unavailable capabilities.
Read the [adapter contract](../_shared/adapter-contract.md) and review the example
stage/forecast definitions. Fill native field mappings, owner ID, record URLs,
targets and any selected pilot capabilities before switching to live.

Codex-compatible skill pointers are tracked in .agents/skills/; Claude slash
command pointers are tracked in .claude/commands/. Work from this repo root.
If a host does not discover those directories, explicitly read AGENTS.md
and invoke the canonical workflow. The workflow remains the authority.

## Optional host integrations

The canonical workflows require readable workspace files, private run storage,
a review surface and the selected adapter capabilities. Hosts that cannot run
Python can use a configured execution environment; report missing capabilities
instead of assuming a tool is installed.

### Perplexity Computer
Install the canonical AGENTS.md, CONTEXT.md, workflows/, _shared/, _templates/
and scripts/ into one new Project, preserving relative paths. Configure the
local deployment files there. Before a run, sync Project Files into the
current sandbox through the host's project-file sync capability.

Create each saved Project skill from the matching .agents/skills/NAME/SKILL.md
pointer. Keep its procedure in Project Files; do not copy the full workflow
into the skill. A standalone pointer without its repository files is incomplete.
Verify the host resolves those paths with a synthetic read-only run.

Perplexity output/{run-id}/ lives in the session sandbox and is shared for
review in the thread. Do not sync it back into reusable Project Files.
Persist or export a run privately only if resumption is required. Across
sessions, pass the exact reviewed artifact explicitly; never assume sandbox
files survive. The configured CRM and mail providers retain external business state.

## Start a run
The task supplies a fresh ID. For example, after choosing `demo-001`:

```bash
python3 scripts/runs.py init demo-001 sales-call-prep
python3 scripts/runs.py status demo-001
```

Follow the workflow selected by [the root router](../CONTEXT.md), then the
[run contract](../workflows/run.md). No external action follows merely from
creating the starter. An example claim cannot be used in live outreach.

## Optional pilot PDF tools

Install `scripts/pilot_usage/requirements.txt` into a virtual environment and
provide an installed Chromium-compatible renderer. Keep its binary path in local
configuration. System fonts work by default; optional custom fonts must be
available locally and match any configured hashes.

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/pilot_usage/requirements.txt
```

The synthetic [pilot fixture](../examples/pilot-usage/CONTEXT.md) exercises the
full assemble-to-PDF path without any customer data or external business effects.
The six pointer skills are complete only with this repository's workflows,
references, policy and helper files. Do not distribute pointer-only ZIPs.
