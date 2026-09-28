# Portable report generation

From the repository, after source capture and review:

```sh
.venv/bin/python workflows/pilot-usage/scripts/pilot_usage.py \
  --run <run> --review <run>/review.json \
  --roster-query <query-id> --activity-query <query-id> \
  --output <run>/outputs/pilot-report --policy _shared/policy.yaml
```

This writes JSON and HTML from the same calculation. Add `--pdf` for a PDF, with
optional `--renderer /absolute/path/to/browser`. Chromium on PATH and standard
macOS Chrome/Edge locations are supported. A temporary browser profile isolates
each print run. The template uses system fonts; no vendor fonts/CDNs are needed.

The default layout is Letter and expands across pages as needed. Printing checks
nonempty content and page dimensions and sets configured title/author metadata.
Render every PDF page to an image and inspect legibility, tables, clipping and page
breaks before sharing. Local checks are not customer approval or delivery evidence.
Brand name, product label, author, accent color and usage unit belong in private
policy. Do not insert another company's logo, collateral or claims by default.
