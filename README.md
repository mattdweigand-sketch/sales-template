# Sales Workflow Template

Five configurable workflows for sales execution, with full procedures,
five task-specific references, and local evidence helpers.
Built with the Interpretable Context Methodology: small routing files, explicit
workflow contracts, shared configuration and editable, human-reviewed run outputs.

Start with [setup](setup/CONTEXT.md). Agents enter through [AGENTS.md](AGENTS.md).

## Workflows
See [the task router](CONTEXT.md) for all five commands and their canonical owners.

## Structure
- `workflows/`: canonical procedures grouped by task family; run.md owns the common review lifecycle.
- `_shared/`: common boundaries and example configuration; deployment values stay local.
- `_templates/`: copied run starter; products live in ignored output/{run-id}/.
- `.agents/skills/` and `.claude/commands/`: generated thin pointers.
- `scripts/` and `tests/`: local checks, wrapper generation and run-state tooling.

## Validate
```bash
python3 scripts/check_repo.py
python3 -m unittest discover -s tests -v
```

No network services are called by these checks. See [portability](setup/portability.md)
for required adapters and the limits of local validation. The template is not
connected to a CRM, mail account, calendar or agent host.
All local helpers use the Python standard library.

## Contribute
Edit the owning workflow or factory file, then update the wrapper registry only
if routing changes. Run `python3 scripts/wrappers.py` to regenerate task maps and pointers,
and validate. Keep examples synthetic and never commit deployment configuration
or run outputs. [MIT license](LICENSE).
