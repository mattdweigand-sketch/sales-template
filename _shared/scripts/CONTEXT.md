# Shared helpers

Deterministic helper paths live in policy.tooling.scripts. Load only the interface
for the selected helper; outputs stay in the external run directory.

## Inputs

| Need | File/Location | Section/Scope |
|---|---|---|
| Helper arguments and guarantees | [interfaces.md](interfaces.md) | Opening guarantees and selected helper row |
| Receipt and field meanings | [adapter contract](../adapter-contract.md) | Selected record/source section |
| Interpreter and review | [interfaces.md](interfaces.md) | "Inputs, outputs and review" |
| Exact CLI flags | Selected helper's --help | Full output |

## Process

1. Resolve the helper path from policy and read only its interface and required data contract.
2. Run it with explicit current-run files and the configured policy.
3. Review its findings beside the underlying evidence; it cannot grant approval.

## Outputs

Mechanical findings or normalized summaries in the external run, as each interface states.
