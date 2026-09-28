# Pipeline presentation helper

Inputs: reviewed `<run>/outputs/pipeline-review.json`, this run's saved coverage JSON
and the configured `_shared/policy.yaml`. The run's existing identity file stays intact.

Process: `pipeline_render.py` validates and formats report, question, receipt or
notification mode. Read its docstring and `--help` for the exact schema and arguments.
The [report rules](../references/report-format.md) own content requirements;
the script owns exact presentation. Shared helper guarantees are in
[interfaces](../../../_shared/scripts/interfaces.md).

Outputs: Markdown to stdout, or notification JSON with a chat delivery hint.
The caller saves output in the external run. Errors emit no partial report.
No connector calls, external writes, notification delivery or scheduling occurs.

Human check: verify sales meaning, approval, source identity and independent readback.
Local validation checks assertions and formatting; it cannot establish those facts.
