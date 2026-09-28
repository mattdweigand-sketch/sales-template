# Maintain one clear home per file

The root contains README, AGENTS, CONTEXT and LICENSE, plus standard hidden Git and
Codex integration files. Setup owns onboarding; workflows own their folder contracts
and procedures; shared owns reusable policy, rules and cross-workflow helpers.
This system folder owns maintenance scripts, tests, dependencies and documentation.

Each workflow starts at `workflows/<name>/CONTEXT.md`: scoped Inputs, short Process,
Checkpoints where approval already applies, Audit checks and explicit Outputs.
Contracts stay at most 80 lines; reference documents stay at most 200 lines.
Detailed instructions live in its `references/procedure.md`;
other references and executable helpers stay beside the workflow that uses them.
These are independent workflows, so there is no mandatory order between them.
Number folders only when their outputs create a real sequential handoff.

## Commands

Run from the repo root, after [installation](../../setup/installation.md):

```sh
.venv/bin/python _system/scripts/wrappers.py
.venv/bin/python _system/scripts/check_repo.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s _system/tests -v
git diff --check
```

Use the absolute repo/interpreter paths when running from elsewhere. Do not rely on
shell activation persisting between calls. The scripts derive the repo root from
their installed location; command examples assume the repo root as working directory.

## Add or change a workflow

Copy [the contract starter](workflow-context-template.md) into its workflow folder
and create only actual supporting files. Declare `cadence`, `reads`,
`writes` and `next` in the contract frontmatter. Add its setup requirements to
`_system/scripts/configuration.py` and its route to `_system/scripts/wrapper-contract.json`.
Run the pointer generator, which also rebuilds the root workflow route table.
Do not hand-edit generated pointers or that table. Preserve command names unless
the user requests a rename. Keep shared rules in their existing owner.

Inputs tables name exact files, policy blocks, rule anchors and reference sections,
including global rules that apply before branch-specific content. Separate stable
references from current-run evidence. Outputs name artifact, location and format.
Audit rows say when a check runs and what passing means. The repository checker
rejects malformed workflow tables, broken scoped links, missing sections, orphan
references, invalid checkpoint steps and oversized contracts/reference documents.

Keep private settings, credentials and run data out of Git. Validate a clean Git
export before distributing the template. Check known external callers before
moving paths; local reference checks cannot discover every downstream clone.
