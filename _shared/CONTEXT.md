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
