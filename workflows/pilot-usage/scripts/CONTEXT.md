# pilot-usage helpers

Inputs: the explicit policy and current-run files named by the owning
[workflow contract](../CONTEXT.md) and its procedure.
Process: run only the helper needed by the selected step, using the repository's
Python environment. These scripts check mechanics and do not call business systems.
Outputs: calculated findings or report artifacts under the selected external run.
Human check: compare results with source evidence and the workflow's review gate.
