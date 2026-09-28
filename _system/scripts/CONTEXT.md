# Repository tools

Inputs: the repository route registry, public files, private setup values when
needed, and explicit source files in an external run.

Process: `setup.py` initializes and checks configuration; `run.py` creates isolated
runs; `receipts.py` captures/verifies source bytes; `wrappers.py` generates pointers
and the root route table; `check_repo.py` checks public structure and references.
`configuration.py` owns the setup schema and `wrapper-contract.json` owns routes.

Outputs: command results, generated routing files, or private run artifacts as named
by the selected command. Run commands from the repo root with `.venv/bin/python`.

Human check: inspect configuration meaning, scope and evidence; mechanical checks
never grant approval or prove provider authenticity. Maintenance starts in
[the contributor guide](../docs/contributing.md).
