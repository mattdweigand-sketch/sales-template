# Sales Workflow Template

A reusable workspace for salespeople working with an AI assistant. It provides
instructions, templates and checks for turning CRM records, email, calendars
and meeting notes into useful sales preparation and follow-up.

The assistant gathers evidence and prepares recommendations. You review and
approve the exact changes before it updates CRM or creates an unsent email
draft. These workflows never send email.

## What you can do

| Task | What you get |
|---|---|
| [Prepare for a sales call](workflows/engagement/sales-call-prep.md) | A brief covering the account, attendees, history and unanswered questions. |
| [Record a completed interaction](workflows/engagement/interaction-sync.md) | A call summary, proposed CRM updates and a follow-up draft. |
| [Review due tasks](workflows/engagement/task-triage-speed-run.md) | Suggested follow-ups, drafts and task changes based on recent activity. |
| [Review the pipeline](workflows/revenue/pipeline-review.md) | Stale or missing deal information and proposed corrections supported by evidence. |
| [Build a quarterly forecast](workflows/revenue/forecast-weekly.md) | Booked deals, deals expected to close, and a path toward your target when set. |

Reviews cite their sources and label missing evidence.

## Start here

You need an AI assistant that can read this workspace. Python 3.9+ and Git run
the local checks. For live work, configure the assistant's access to your CRM,
email and calendar; this repository does not install those connections.

1. Read the [fictional example review](examples/review.md) to see a small example of the output.
2. Follow [installation and setup](setup/installation.md). Configure your sales settings and service access, then check the setup with fictional test data before using live records.
3. Ask your assistant to read [AGENTS.md](AGENTS.md), choose a workflow from [the task list](CONTEXT.md), and work on your specific call, tasks or accounts.

Each task gets its own local folder under `output/` for the request, source
evidence, review and results. Deployment settings and task outputs are ignored
by Git so they stay separate from the reusable template.

## Repository map

```text
sales-template/
├── README.md                    Overview and starting point for people
├── AGENTS.md                    Starting instructions for AI assistants
├── CONTEXT.md                   List of workflows and where to find them
├── setup/                       Installation and configuration guides
├── workflows/
│   ├── engagement/              Call prep, interaction notes and follow-up tasks
│   ├── revenue/                 Pipeline reviews and quarterly forecasts
│   └── run.md                   How a task moves through review and approval
├── _shared/                     Common rules, example settings and data formats
├── _templates/run/              Blank files copied when starting a task
├── examples/                    Fictional review example
├── scripts/                     Local validation, calculations and task tools
├── tests/                       Tests using fictional data
├── .agents/skills/              Generated workflow shortcuts for agents
├── .claude/commands/            Generated workflow shortcuts for Claude
├── .github/workflows/           Automated repository checks
├── AUDIT-REMEDIATION-SPEC.md     Maintainer audit and verification record
└── output/                     Local task folders; created during use, Git-ignored
```

## Check the repository

Run from the repository root:

```bash
python3 scripts/check_repo.py
python3 -m unittest discover -s tests -v
```

These checks use local files and fictional test data; they do not call live services.
The Python helpers use the standard library, with no extra Python packages.

For changes to workflows or helpers, see [the tooling guide](scripts/CONTEXT.md).
For deployment requirements, see [portability](setup/portability.md).
Keep examples fictional and customer data out of commits. [MIT license](LICENSE).
