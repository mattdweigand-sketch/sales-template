# Synthetic pilot delivery

One job: exercise the full pilot report locally without a connector.
Inputs: [results.json](results.json), [narrative-review.json](narrative-review.json),
and the example policy. Every person, organization and task is synthetic.

Process: run the integration test below. It copies the fixture into a temporary
directory, marks a test-only review approved in memory, then assembles, computes,
validates, renders and prints through the actual helpers. It never edits the
example review or authorizes customer work.

```bash
PILOT_PDF_RENDERER=/path/to/chromium .venv/bin/python -m unittest discover -s tests -p test_pilot_delivery.py -v
```

Outputs: a temporary two-page PDF and HTML, removed after the test. Use the pilot
workflow's commands with an explicit private output directory to retain a sample.
Human check: the delivery test checks the PDF structure and text; inspect both
rendered pages whenever the template changes. No synthetic claim may enter outreach.
