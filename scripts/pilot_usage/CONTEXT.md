# Pilot report pipeline

One job: turn one pilot's complete saved source results and reviewed narratives
into reconciled metrics, HTML and a verified PDF.

Inputs: the selected run's source results, narrative-review.json and configured
policy. Follow [the pilot workflow](../../workflows/revenue/pilot-usage.md) and
its [PDF reference](../../workflows/revenue/references/pilot-usage-pdf-format.md).

Process: assemble → compute → validate → render → print → visually inspect.
Stop on a failed step. No connector calls or dependency downloads occur here.
Only print requires optional packages in [requirements.txt](requirements.txt).

Outputs: files in ignored output/{run-id}/pilot-usage/ or a private external
directory. Neither source rows nor generated deliverables belong in the factory.

Human check: review scope, display names, categories and narratives in the
conversation before setting the review flag. Inspect both PDF pages before delivery.
