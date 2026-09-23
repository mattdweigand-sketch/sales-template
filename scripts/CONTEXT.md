# Local tooling

Inputs: scripts/wrapper-contract.json, canonical workflow paths, and the explicitly selected local run.
Process and ownership:

| Tool | Job |
|---|---|
| wrappers.py | Generate/check root and family task maps, .agents skill pointers and .claude command pointers |
| runs.py | Copy a run starter, record an existing review reference, inspect local run state |
| check_repo.py | Check links, contract shape, wrapper parity and public-template hygiene |

Outputs: generated wrappers or output/{run-id}/ artifacts, according to the invoked command.
Human check: review the diff; a passing static check does not approve external actions.
Run `python3 scripts/check_repo.py` and `python3 -m unittest discover -s tests -v`.
The tools use Python 3.9+ standard library and make no network requests.
