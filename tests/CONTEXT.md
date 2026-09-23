# Regression tests

Inputs: repository templates and temporary synthetic fixtures.
Process: `python3 -m unittest discover -s tests -v`.
Outputs: test results; temporary directories are discarded by the test runner.
Human check: inspect failures and their effect on run isolation, review invalidation and wrapper routing.
These tests never call live connectors or prove provider success.

Coverage: review dependencies, complete source receipts, date and event timing,
mail direction and replies, pilot rounding/reconciliation and rejected inputs.
The optional `test_pilot_delivery.py` uses pypdf and `PILOT_PDF_RENDERER` for a
real two-page PDF integration check. It launches a separate temporary browser
profile, never the user's browser session. Without those dependencies the test
is explicitly skipped; core behavior remains tested with the standard library.
