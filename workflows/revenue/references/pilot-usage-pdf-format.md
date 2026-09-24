# Pilot usage PDF

Two Letter pages, light theme, generic sans-serif/monospace type and the configured palette. Page 1 is the numbers. Page 2 is what the work was. Every number on both pages is computed by the scripts from the normalized roster, activities and optional allocations. Prose comes only from the approved review file.

## Page 1

Header with customer name, prepared date, pilot window, data-through day of pilot. Four tiles. Participants active of roster, activity count, measured quantity with its configured unit, days with activity. Scope callout. Usage by user table sorted by measured quantity, with initial-period and after columns (initial length comes from policy.pilot_usage.pdf.week_one_length_days). Activities-per-day bar chart. Usage highlights, two computed bullets first, then the approved ones, then re-engagement and allocation balance computed only when an allocation exists.

## Page 2

Where the work went. Stacked share bar and one row per category with activity counts, measured quantity, share, description. Representative work, four cards. What the pattern shows, short paragraphs. Business value delivered, labeled bullets. Source note footer.

## Review file

JSON at `<run>/pilot-usage/narrative-review.json`. Draft it, show it, wait for approval.

```
{
  "customer_name": "<Account name as the customer writes it>",
  "scope_id": "<verified stable pilot scope>",
  "prepared_by": "<your name>",
  "pilot_end": "<verified pilot end, ISO>",
  "pilot_start": "<verified pilot start, ISO>",
  "data_through": "<reviewed reporting-local date, ISO>",
  "confidentiality_label": "Confidential",
  "approved": false,
  "display_names": {"<user_id>": "<Contact name>"},
  "participation_notes": {"<user_id>": "<one line, optional>"},
  "categories": [{"category_id": "<slug>", "label": "<Title case>", "description": "<one sentence>"}],
  "activity_categories": {"<activity_id>": "<category_id>"},
  "narratives": {
    "scope_note": "<one or two sentences>",
    "usage_highlights": [{"label": "<Short label>", "text": "<one sentence>"}],
    "representative_work": [{"title": "<short>", "user_ids": ["<user_id>"], "summary": "<one or two sentences>"}],
    "work_interpretation": ["<paragraph>", "<paragraph>"],
    "business_value": [{"label": "<Short label>", "text": "<one sentence>"}],
    "source_note": "<one sentence on source and measurement unit>"
  }
}
```

Rules. At most six categories, palette order from policy. An activity with no entry in `activity_categories` lands in the uncategorized category. Four representative work cards. Two to four work-interpretation paragraphs. Every narrative claim must trace to a activity description, a CRM field, or a computed number. No query text, no client or matter names beyond what the activity descriptions already state, no measurements or counts typed by hand.

## Approval

Show in chat, numbered. 1 categories with activity counts. 2 display names. 3 narratives. Wait. Edit the file on corrections. Set `approved: true` only on approval. The pipeline refuses an unapproved file.

## Pipeline

Scripts in `policy.tooling.scripts.pilot_usage_pdf`, run from the reusable workspace files checkout, all outputs under `output_dir`.

```
assemble_pilot_usage_input.py --review <dir>/narrative-review.json --results <dir>/results.json --policy _shared/policy.json --output <dir>/input.json
compute_pilot_usage_report.py  --input <dir>/input.json --policy _shared/policy.json --output <dir>/report.json
validate_pilot_usage_report.py --input <dir>/input.json --policy _shared/policy.json --report <dir>/report.json
render_pilot_usage_report.py   --input <dir>/input.json --policy _shared/policy.json --report <dir>/report.json --output <dir>/report.html
print_pilot_usage_pdf.py       --html <dir>/report.html --policy _shared/policy.json --output <dir>/<account-slug>-pilot-usage.pdf
```

Assemble accepts complete normalized results via `--results`, or an explicit
normalized saved-call directory via `--tool-calls`. See the
[analytics contract](pilot-usage-queries.md) for dataset and receipt schemas.
Normalized input/report schema is version 2. `usage_units` are integers at the
configured decimal precision; the renderer restores the unit's decimal scale.
A missing allocation stays null and produces no balance claim. The input records
the metric definition; changing the policy metric requires reassembly and review.
Print validates two Letter pages and metadata and retains an older output on
failure. System fonts are default; optional local fonts are hash checked.

Run the commands with `python3 scripts/pilot_usage/<script>` from the repository root. PDF printing requires the optional dependencies in `scripts/pilot_usage/requirements.txt` and an installed Chromium binary (`--renderer <path>` when not on PATH). Render and visually inspect both pages after printing; page count alone cannot detect clipping. Keep the narrative review separate from the run lifecycle's `review.json`. Declare the narrative review, normalized input, results and delivered PDF as run artifacts. The approved flag records an actual conversation review; it is not itself authorization.
