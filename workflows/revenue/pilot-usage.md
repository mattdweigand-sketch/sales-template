# Pilot Usage

Summarize one pilot's adoption from a configured analytics source.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Collection requirements use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

Answers one question for one pilot: is it being used, by whom, for what. Read-only. The configured business record identifies the pilot; the analytics adapter supplies the measurements. This workflow writes to neither source.

Two modes. `report` (default) prints in chat. `pdf` builds the two-page customer deliverable. Pick `pdf` when the request says pdf, deliverable, customer report, or send to the customer.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. Make the reusable workspace files available through the configured host before starting. Confirm policy.pilot_usage.enabled, the permitted metrics, audience and adapter mappings before live collection. Record the selected scope in the run request. Read [references/pilot-usage-queries.md](references/pilot-usage-queries.md) for the normalized collection contract. Read [references/pilot-usage-report-format.md](references/pilot-usage-report-format.md) for `report` mode. Read [references/pilot-usage-pdf-format.md](references/pilot-usage-pdf-format.md) for `pdf` mode.

### 2. Resolve the pilot

The request must identify one pilot or evaluation under `policy.pilot_usage.scope`.
Resolve its customer record, stable analytics `scope_id`, start/end dates and
permitted audience through the configured adapter or explicit user-supplied
source evidence. The scope may identify an account, project, site or subscription.
More than one match requires clarification. A missing or unverified scope blocks
analytics collection; do not guess a scope from a name. Record explicit ISO
`pilot_start`, `pilot_end` and `data_through` in the reporting timezone. A paid
trial, provisioned organization or allocation is not a prerequisite.

### 3. Pull

Use the configured read-only analytics adapter and the
[collection contract](references/pilot-usage-queries.md). Apply the verified scope,
reviewed dates and internal-participant exclusions to every dataset. Keep native
requests, complete source results, terminal success and pagination evidence.

- `report` mode retrieves the permitted roster, activity, feature-mix and use-case
  sections. Feature labels and measurement grain come from the deployment.
- `pdf` mode retrieves `roster`, `activities` and optional `allocations`. Each
  activity has one stable ID, attributed participant, reporting-local date and
  quantity in `policy.pilot_usage.metric.unit`. Quantities must not mix units.

Follow the provider's documented completion mechanism. An asynchronous submission
is not success. A configured timeout or failed query makes that chat section
unavailable with its reason. A failed PDF source stops the build, including an
allocation query that was attempted; absence of an optional allocation is distinct
from a failed lookup. No allocation field or credit grant is required when none
applies to the configured metric.

### 4a. Report mode

Plain text per [references/pilot-usage-report-format.md](references/pilot-usage-report-format.md). Use cases: cluster the sample into at most five themes, each with a count and one short audience-permitted example verbatim. Skip file names, JSON, and single words. Then one line from `NextSteps` on what the buyer said they wanted.

### 4b. PDF mode

1. Pull CRM Contacts on the Account for display names. A participant with no matching Contact keeps the source display name or stable ID.
2. Draft the review file per [references/pilot-usage-pdf-format.md](references/pilot-usage-pdf-format.md) into `policy.pilot_usage.pdf.output_dir`. Categories, activity categories, display names, and every narrative are your drafts from the activity descriptions and rows.
3. Show the drafts in chat, numbered, and wait. Set `approved: true` only after the user approves. Apply corrections to the file, not to the scripts.
4. Run the pipeline in `policy.tooling.scripts.pilot_usage_pdf`, in order: `assemble_pilot_usage_input.py`, `compute_pilot_usage_report.py`, `validate_pilot_usage_report.py`, `render_pilot_usage_report.py`, `print_pilot_usage_pdf.py`. Assemble and validate print status JSON; compute and render write their declared output files; print returns PDF inspection JSON. Stop on any non-zero exit or `"valid": false` and report the problem verbatim.
5. Inspect both rendered pages for clipped or overlapping text, then share the PDF in the thread. Outputs stay in `output_dir`. Nothing enters reusable workspace files.

### 5. Close

One line. Pilot reported, mode, and `Nothing written`. In `pdf` mode add the measured usage with its unit and any applicable allocation and the PDF path.

### Refuse

Any business-record or analytics write. Emailing or drafting outreach. Guessing an analytics scope from a name match. Running more than the one named pilot. Printing query text or a query string over 120 characters anywhere, including the PDF. Setting `approved: true` before the user approves. Saving PDF, HTML, or JSON outputs to reusable workspace files.

## Outputs and readiness

Save the pilot readout and source gaps in `output/{run-id}/01_review.md`, with
PDF artifacts in the configured run output directory. Complete the mode-specific
checks above, share the deliverable and record this read-only review through the
[run lifecycle](../run.md).

## Human check

Check the pilot scope, reconciled totals and use-case interpretations. In PDF
mode, approve the draft narratives and categories before building, then inspect
both pages before sharing.
