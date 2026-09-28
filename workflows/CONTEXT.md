# Sales workflows

Each child folder performs one kind of sales task. Choose it through the generated
[root workflow map](../CONTEXT.md), then read its `CONTEXT.md` for inputs, process,
outputs and human check. The workflows have independent entry points; numbering
them would imply an execution order they do not have.

Inputs: the named task, configured shared policy and this run's source evidence.
Process: execute only the selected workflow and its declared dependencies.
Outputs: editable review artifacts in the unique external run, plus any separately
approved effects. CRM remains the business system of record.
Human check: use the selected contract's review gate; prior run files and approvals
do not establish completion or authority for a new run.
