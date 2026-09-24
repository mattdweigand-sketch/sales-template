# Local tooling

Inputs: scripts/wrapper-contract.json, canonical workflow paths, and the explicitly selected local run.
Process and ownership:

| Tool | Job |
|---|---|
| wrappers.py | Generate/check root and family task maps, .agents skill pointers and .claude command pointers |
| runs.py | Initialize, validate bound inputs/effects, record an existing review, inspect recovery state |
| check_repo.py | Check links, contract shape, wrapper parity and public-template hygiene |
| coverage_check.py | Check complete paired current-run source receipts and pagination for pipeline and forecast |
| hygiene_check.py | Calculate next-step dates, required-field gaps, linked activity and mechanical triggers |
| mail_contact_stats.py | Count complete paired mail history with source-linked reply classification |
| mail_thread_digest.py | Produce bounded navigation excerpts; full bodies remain decision evidence |
| forecast_math.py | Compute Decimal totals and the shortest reviewed Upside path |
| forecast_assessment.py | Check recorded buyer timing, quotes and contradictions through runs.py; meaning remains reviewed |
| triage_check.py | Compute fixed Task groups and local calendar dates from established facts |

Read the relevant [adapter data contract](../_shared/adapter-contract.md) before
normalizing inputs. Helpers operate on explicit run files. Their output is
evidence for review, not permission to write. The route registry lists each
workflow's review dependencies so changed references or helper code invalidate
its recorded approval.

Outputs: generated wrappers or output/{run-id}/ artifacts, according to the invoked command.
Human check: review the diff; a passing static check does not approve external actions.
Run `python3 scripts/check_repo.py` and `python3 -m unittest discover -s tests -v`.
Core tools use Python 3.9+ standard library and make no network requests.
