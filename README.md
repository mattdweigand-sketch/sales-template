# sales-template

Seven reusable sales workflows for **Codex**: prepare for calls, log meeting
outcomes, review tasks and pipeline, forecast, report pilot usage, and close signed
deals. The agent gathers evidence, explains gaps and presents exact changes for
review. Email drafts remain unsent. Every external effect requires its own
applicable approval and independent verification.

Bring your company's sales process and connect the systems you actually use.
The template includes neutral examples and logical data contracts, with no company
pricing, product claims, private service endpoints or required CRM vendor. Setup
maps your native records, stages, fields, fiscal calendar and available tools.
It does not install integrations or claim compatibility before those mappings work.

| Choose in the `/` skill menu | What it does |
|---|---|
| sales-call-prep | Prepare a read-only account and meeting brief |
| interaction-sync | Propose CRM changes and an unsent draft after one call |
| task-triage-speed-run | Review due, overdue and undated sales tasks |
| pipeline-review | Find stale records and propose evidence-backed corrections |
| forecast-weekly | Review forecast buckets and calculate a path to target |
| pilot-usage | Analyze configured usage data or supplied exports; prepare a report/PDF |
| close | Review signed terms, won-state changes and configured downstream steps |

Each small SKILL.md points to one workflow contract. Open the repository as a Codex project,
type `/` and select a skill, or explicitly invoke `$sales-call-prep`, for example.

## Start here

Install Python 3.10 or newer first; 3.12 is the validated baseline. Run these
commands from the repo root. If `python3.12` is not on PATH, use the absolute path
to your installed Python 3.10+ for the first command. Subsequent commands use the
repo virtual environment directly; shell activation is unnecessary.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r _system/requirements.txt
.venv/bin/python _system/scripts/setup.py init
.venv/bin/python _system/scripts/check_repo.py
.venv/bin/python -m unittest discover -s _system/tests -v
```

Then ask: **“Set up this sales workspace for the workflows I use.”** The
[setup interview](setup/CONTEXT.md) collects only missing answers and writes private
settings, preserving existing configuration. [Installation](setup/installation.md)
covers runtime, skill discovery, optional PDF support and clean exports.
Upgrading an older workspace? Follow [migration](setup/migration.md) before setup.

```sh
.venv/bin/python _system/scripts/setup.py doctor --workflow sales-call-prep
.venv/bin/python _system/scripts/run.py init sales-call-prep
```

Doctor reports missing configuration. Verify actual tool availability and access in
the current chat before live use. The run command prints a unique external directory
for raw evidence, normalized receipts and outputs. No customer data belongs here.
[Adapter contracts](setup/adapters.md) explain field mapping, scope and pagination.

## Repository map

Four areas, each with one purpose:

```text
sales-template/
    ├── README.md          # Start here
    ├── AGENTS.md          # Codex entry point
    ├── CONTEXT.md         # Choose a workflow
    ├── LICENSE
    ├── setup/             # Configure your workspace
    ├── workflows/         # Sales work
    │   ├── sales-call-prep/
    │   ├── interaction-sync/
    │   ├── task-triage-speed-run/
    │   ├── pipeline-review/
    │   ├── forecast-weekly/
    │   ├── pilot-usage/
    │   └── close/
    ├── _shared/           # Policy, rules and shared helpers
    ├── _system/           # Template maintenance
    │   ├── scripts/
    │   ├── tests/
    │   ├── docs/
    │   └── requirements.txt
    ├── .agents/skills/    # Codex command pointers
    └── .github/workflows/ # Automated checks
```

Each workflow opens with `CONTEXT.md`: scoped inputs, process, review checkpoints,
audit checks and outputs. Checkpoints preserve the workflow's existing approvals.
Its `references/` holds the detailed procedure and supporting guidance; `scripts/`
exists only where that workflow needs a helper. Choose a workflow by the task at
hand. These seven workflows do not have one mandatory execution order.

Pipeline review checks Task actions in daily and extended modes. It separates clear
recommendations from questions, walks questions one at a time, and uses one renderer
for reports, approval options and write receipts. Its labels and working data stay
in the external run. The renderer formats reviewed facts; it does not approve or
execute changes. Existing users should follow the [pipeline upgrade notes](setup/migration.md#pipeline-presentation-update).

The structure follows ICM's layered context pattern: a small entry point, a routing
map, folder contracts, then selected references and current-run evidence. Customer
evidence and editable reports stay in the external run directory. Private settings
remain in `_shared/` and are ignored by Git.

**Navigate:** [Setup](setup/CONTEXT.md) · [Skills](.agents/skills) ·
[Workflows](workflows) · [Shared rules](_shared/rules.md) ·
[Validation](_system/docs/validation.md)

## What is configurable

Company/product identity, seller, timezone, internal domains, writing voice, stages,
required fields, cadence, fiscal quarters, currency, targets and native mappings.
Pilot units and activity grain come from your source; no billing conversion is
assumed. Branding uses system fonts and configurable labels/colors. Close handoffs
and provisioning are optional and disabled until explicitly configured and approved.
Schedules are inert until requested through Codex.

Tests use fictional data and check local mechanics. They cannot prove live access,
source authenticity, buyer intent, human approval, message delivery or provisioning
success. Unsupported required mappings remain gaps. See [validation](_system/docs/validation.md)
and [provenance](_system/docs/provenance.md) for scope and limits.
