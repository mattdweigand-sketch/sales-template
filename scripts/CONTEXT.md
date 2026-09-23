# Local tooling

Inputs: scripts/wrapper-contract.json, canonical workflow paths, and the explicitly selected local run.
Process and ownership:

| Tool | Job |
|---|---|
| wrappers.py | Generate/check root and family task maps, .agents skill pointers and .claude command pointers |
| runs.py | Copy a run starter, record an existing review reference, inspect local run state |
| check_repo.py | Check links, contract shape, wrapper parity and public-template hygiene |
| coverage_check.py | Check complete paired current-run source receipts and pagination for pipeline and forecast |
| hygiene_check.py | Calculate next-step dates, required-field gaps, linked activity and mechanical triggers |
| gmail_contact_stats.py | Count sent, inbound and unanswered messages from explicit saved mail results |
| gmail_thread_digest.py | Reduce newest message bodies without quoted history or signed URL parameters |
| [pilot_usage/](pilot_usage/CONTEXT.md) | Assemble, compute, validate, render and print a reviewed pilot report |

Read the relevant [adapter data contract](../_shared/adapter-contract.md) before
normalizing inputs. Helpers operate on explicit run files, never an implicit
Perplexity session directory. Their output is evidence for review, not permission
to write. The route registry lists each workflow's review dependencies so changed
references or helper code invalidate its recorded approval.

Outputs: generated wrappers or output/{run-id}/ artifacts, according to the invoked command.
Human check: review the diff; a passing static check does not approve external actions.
Run `python3 scripts/check_repo.py` and `python3 -m unittest discover -s tests -v`.
Core tools use Python 3.9+ standard library and make no network requests.
PDF printing additionally uses pypdf and a locally installed Chromium binary.
