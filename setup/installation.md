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
targets and the selected workflow capabilities before switching to live.

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
Install an intact clean export of the reviewed repository into one new Project,
preserving relative paths and hidden directories. Include setup/, examples/,
tests/, .agents/, .claude/, the root files and all their dependencies. A partial
file list breaks navigation and local validation. From the reviewed checkout:

```bash
python3 scripts/check_repo.py
git archive --format=tar --output=../sales-template-reviewed.tar HEAD
```

Extract that archive into a new empty directory and run the README validation
commands there before uploading it. `HEAD` means the reviewed commit; uncommitted
edits are not exported. Check that the archive contains no deployment files,
credentials, output/, or caches. A clean Git export omits ignored/untracked local
material; the repository check must also reject accidentally tracked private files.

Configure the local deployment files in the installed copy. Before a run, sync
Project Files into the current sandbox through the host's project-file sync
capability. Verify path and hidden-file support in that deployment; the template
does not establish the host's capabilities.

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

Fill the run's inputs.json with its real saved sources and proposed effects,
then run `python3 scripts/runs.py validate demo-001` before recording review.
An incomplete report can be reviewed with explicit gaps and no effects; an
authored ready flag is not a replacement for the required checks.

The five pointer skills require this repository's workflows, references, policy
and helper files. Do not distribute pointer-only ZIPs.
