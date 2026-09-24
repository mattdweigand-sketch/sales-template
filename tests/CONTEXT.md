# Regression tests

Inputs: repository templates and temporary synthetic fixtures.
Process: `python3 -m unittest discover -s tests -v`.
Outputs: test results; temporary directories are discarded by the test runner.
Human check: inspect failures and their effect on run isolation, review invalidation and wrapper routing.
These tests never call live connectors or prove provider success.

Coverage: review dependencies, complete source receipts, date and event timing,
mail direction and replies, and rejected inputs. All checks use the Python
standard library.
