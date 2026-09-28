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

Each small SKILL.md points to one procedure. Open the repository as a Codex project,
type `/` and select a skill, or explicitly invoke `$sales-call-prep`, for example.

## Start here

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/setup.py init
.venv/bin/python scripts/check_repo.py
.venv/bin/python -m unittest discover -s tests -v
```

Then ask: **“Set up this sales workspace for the workflows I use.”** The
[setup interview](setup/CONTEXT.md) collects only missing answers and writes private
settings, preserving existing configuration. [Installation](setup/installation.md)
covers runtime, skill discovery, optional PDF support and clean exports.

```sh
.venv/bin/python scripts/setup.py doctor --workflow sales-call-prep
.venv/bin/python scripts/run.py init sales-call-prep
```

Doctor reports missing configuration. Verify actual tool availability and access in
the current chat before live use. The run command prints a unique external directory
for raw evidence, normalized receipts and outputs. No customer data belongs here.
[Adapter contracts](setup/adapters.md) explain field mapping, scope and pagination.

## Repository map

The tree below shows every tracked folder and file. Skill pointers live in
`.agents/skills/`; their full procedures live in `workflows/`.

```text
sales-template/
├── .agents/
│   └── skills/
│       ├── close/
│       │   └── SKILL.md
│       ├── forecast-weekly/
│       │   └── SKILL.md
│       ├── interaction-sync/
│       │   └── SKILL.md
│       ├── pilot-usage/
│       │   └── SKILL.md
│       ├── pipeline-review/
│       │   └── SKILL.md
│       ├── sales-call-prep/
│       │   └── SKILL.md
│       └── task-triage-speed-run/
│           └── SKILL.md
├── .github/
│   └── workflows/
│       └── validate.yml
├── _shared/
│   ├── collateral/
│   │   └── README.md
│   ├── scripts/
│   │   ├── _saved_json.py
│   │   ├── coverage_check.py
│   │   ├── hygiene_check.py
│   │   ├── mail_contact_stats.py
│   │   ├── mail_evidence.py
│   │   ├── mail_thread_digest.py
│   │   └── README.md
│   ├── adapter-contract.md
│   ├── adapters.example.json
│   ├── CONTEXT.md
│   ├── policy.example.yaml
│   └── rules.md
├── _templates/
│   └── workflow/
│       └── procedure.md
├── scripts/
│   ├── check_repo.py
│   ├── receipts.py
│   ├── run.py
│   ├── setup.py
│   ├── wrapper-contract.json
│   └── wrappers.py
├── setup/
│   ├── adapters.md
│   ├── automations.md
│   ├── CONTEXT.md
│   ├── installation.md
│   └── questionnaire.md
├── tests/
│   ├── test_closeout_check.py
│   ├── test_codex_setup.py
│   ├── test_coverage_check.py
│   ├── test_evidence_helpers.py
│   ├── test_forecast_math.py
│   ├── test_forecast_notify.py
│   ├── test_hygiene_check.py
│   ├── test_pilot_usage.py
│   ├── test_skill_procedures.py
│   └── test_triage_check.py
├── workflows/
│   ├── close/
│   │   ├── references/
│   │   │   ├── fields.md
│   │   │   ├── paths.md
│   │   │   └── provisioning.md
│   │   └── procedure.md
│   ├── forecast-weekly/
│   │   ├── references/
│   │   │   ├── forecast-assessment.md
│   │   │   └── report-format.md
│   │   ├── scripts/
│   │   │   ├── forecast_math.py
│   │   │   └── forecast_notify.py
│   │   └── procedure.md
│   ├── interaction-sync/
│   │   └── procedure.md
│   ├── pilot-usage/
│   │   ├── references/
│   │   │   ├── data-contract.md
│   │   │   ├── pdf-format.md
│   │   │   └── report-format.md
│   │   ├── scripts/
│   │   │   └── pilot_usage.py
│   │   └── procedure.md
│   ├── pipeline-review/
│   │   ├── references/
│   │   │   ├── collect.md
│   │   │   └── report-format.md
│   │   └── procedure.md
│   ├── sales-call-prep/
│   │   ├── references/
│   │   │   └── brief-formats.md
│   │   └── procedure.md
│   └── task-triage-speed-run/
│       ├── references/
│       │   └── crm-corrections.md
│       ├── scripts/
│       │   ├── closeout_check.py
│       │   └── triage_check.py
│       └── procedure.md
├── .gitignore
├── AGENTS.md
├── CONTEXT.md
├── LICENSE
├── PROVENANCE.md
├── README.md
├── requirements.txt
└── VALIDATION.md
```

**Navigate:** [Setup](setup/CONTEXT.md) · [Skills](.agents/skills/) ·
[Workflows](workflows/) · [Shared rules](_shared/rules.md) ·
[Helpers](_shared/scripts/README.md) · [Validation](VALIDATION.md)

Setup creates private `_shared/policy.yaml` and `_shared/adapters.json`, which Git
ignores. Each run stores evidence (`raw/`), normalized receipts (`calls/`) and
reports (`outputs/`) in a separate directory outside the repo. These generated
files are not part of the tree above.

To add a workflow, start from [_templates/workflow/](_templates/workflow/), register
it in [scripts/wrapper-contract.json](scripts/wrapper-contract.json), then run
`python scripts/wrappers.py` to generate its skill pointer.

## What is configurable

Company/product identity, seller, timezone, internal domains, writing voice, stages,
required fields, cadence, fiscal quarters, currency, targets and native mappings.
Pilot units and activity grain come from your source; no billing conversion is
assumed. Branding uses system fonts and configurable labels/colors. Close handoffs
and provisioning are optional and disabled until explicitly configured and approved.
Schedules are inert until requested through Codex.

Tests use fictional data and check local mechanics. They cannot prove live access,
source authenticity, buyer intent, human approval, message delivery or provisioning
success. Unsupported required mappings remain gaps. See [validation](VALIDATION.md)
and [provenance](PROVENANCE.md) for scope and limits.
