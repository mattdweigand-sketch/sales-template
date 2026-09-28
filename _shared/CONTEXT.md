# Shared context

| File | Owner |
|---|---|
| policy.example.yaml | Neutral template defaults; maintainers |
| policy.yaml | Ignored deployment values; user through setup |
| adapters.example.json | Empty capability/mapping scaffold; maintainers |
| adapters.json | Ignored actual provider contracts; user through setup |
| rules.md | Shared evidence and approval boundaries |
| adapter-contract.md | Logical record and completeness contracts |
| scripts/ | Deterministic checks shared by workflows |

One home per value, rule and mapping. Never store customer evidence or credentials here.

## Inputs and process

Read only the private policy blocks and rule anchors named by the selected workflow
contract. Examples seed setup; they are not deployment facts. Use the adapter data
contract for normalized evidence and [helper contracts](scripts/CONTEXT.md) for
mechanical checks. Rules and configuration each have one canonical home here.

## Outputs and human check

This folder contains reusable reference material and ignored private configuration.
It never stores customer evidence or run outputs. Review changed policy and mapping
meaning through [setup](../setup/CONTEXT.md); a helper result cannot grant approval.
