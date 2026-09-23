# Pilot usage PDF

Two Letter pages, light theme, generic sans-serif/monospace type and the configured palette. Page 1 is the numbers. Page 2 is what the work was. Every number on both pages is computed by the scripts from queries 1, 4, and 5. Prose comes only from the approved review file.

## Page 1

Header with customer name, prepared date, pilot window, data-through day of pilot. Four tiles. Users active of seats, tasks, credits used, days with activity. Scope callout. Usage by user table sorted by credits, with week-one and after columns. Tasks-started-per-day bar chart. Usage highlights, two computed bullets first, then the approved ones, then re-engagement and credit runway computed.

## Page 2

Where the work went. Stacked share bar and one row per category with tasks, credits, share, description. Representative work, four cards. What the pattern shows, short paragraphs. Business value delivered, labeled bullets. Source note footer.

## Review file

JSON at `<run>/pilot-usage/narrative-review.json`. Draft it, show it, wait for approval.

```
{
  "customer_name": "<Account name as the customer writes it>",
  "organization_uuid": "<from CRM>",
  "prepared_by": "<your name>",
  "pilot_end": "<TrialEndDate, ISO>",
  "pilot_start": "<optional, default earliest non-voided grant>",
  "data_through": "<optional, default yesterday>",
  "confidentiality_label": "Confidential",
  "approved": false,
  "display_names": {"<email>": "<Contact name>"},
  "participation_notes": {"<email>": "<one line, optional>"},
  "categories": [{"category_id": "<slug>", "label": "<Title case>", "description": "<one sentence>"}],
  "task_categories": {"<context_uuid>": "<category_id>"},
  "narratives": {
    "scope_note": "<one or two sentences>",
    "usage_highlights": [{"label": "<Short label>", "text": "<one sentence>"}],
    "representative_work": [{"title": "<short>", "user_emails": ["<email>"], "summary": "<one or two sentences>"}],
    "work_interpretation": ["<paragraph>", "<paragraph>"],
    "business_value": [{"label": "<Short label>", "text": "<one sentence>"}],
    "source_note": "<one sentence on source and credit unit>"
  }
}
```

Rules. At most six categories, palette order from policy. A task with no entry in `task_categories` lands in the uncategorized category. Four representative work cards. Two to four work-interpretation paragraphs. Every narrative claim must trace to a task title, a CRM field, or a computed number. No query text, no client or matter names beyond what the task titles already state, no credits or counts typed by hand.

## Approval

Show in chat, numbered. 1 categories with task counts. 2 display names. 3 narratives. Wait. Edit the file on corrections. Set `approved: true` only on approval. The pipeline refuses an unapproved file.

## Pipeline

Scripts in `policy.tooling.scripts.pilot_usage_pdf`, run from the Project Files checkout, all outputs under `output_dir`.

```
assemble_pilot_usage_input.py --review <dir>/narrative-review.json --results <dir>/results.json --policy _shared/policy.json --output <dir>/input.json
compute_pilot_usage_report.py  --input <dir>/input.json --policy _shared/policy.json --output <dir>/report.json
validate_pilot_usage_report.py --input <dir>/input.json --policy _shared/policy.json --report <dir>/report.json
render_pilot_usage_report.py   --input <dir>/input.json --policy _shared/policy.json --report <dir>/report.json --output <dir>/report.html
print_pilot_usage_pdf.py       --html <dir>/report.html --policy _shared/policy.json --output <dir>/<account-slug>-pilot-usage.pdf
```

Assemble accepts complete normalized results via `--results`, or the explicit saved warehouse directory via `--tool-calls`; no implicit session path is scanned. Normalized result keys are `q1_roster`, `q4_grants`, `q5_tasks`, each an array with the query output columns below. Keep native terminal and pagination receipts beside them. Print uses an installed Chromium binary, validates two Letter pages and metadata, and retains an older output on failure. The default uses system fonts. Optional locally supplied fonts are hash checked; no branded fonts or font downloads are included.

Run the commands with `python3 scripts/pilot_usage/<script>` from the repository root. PDF printing requires the optional dependencies in `scripts/pilot_usage/requirements.txt` and an installed Chromium binary (`--renderer <path>` when not on PATH). Render and visually inspect both pages after printing; page count alone cannot detect clipping. Keep the narrative review separate from the run lifecycle's `review.json`. Declare the narrative review, normalized input, results and delivered PDF as run artifacts. The approved flag records an actual conversation review; it is not itself authorization.
