# Pilot Usage

Summarize one pilot's adoption from a configured analytics source.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Query sketches use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

Answers one question for one pilot: is it being used, by whom, for what. Read-only. CRM names the pilot, the warehouse supplies the numbers, this skill writes nothing to either.

Two modes. `report` (default) prints in chat. `pdf` builds the two-page customer deliverable. Pick `pdf` when the request says pdf, deliverable, customer report, or send to the customer.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. In a hosted project, sync the reusable files first. Record the selected scope in the run request. Read [references/pilot-usage-queries.md](references/pilot-usage-queries.md) for the SQL templates. Read [references/pilot-usage-report-format.md](references/pilot-usage-report-format.md) for `report` mode. Read [references/pilot-usage-pdf-format.md](references/pilot-usage-pdf-format.md) for `pdf` mode.

### 2. Resolve the pilot

The request must name one Account. If it names none, ask which pilot before running anything. Never run every pilot.

`SELECT Id, Name, StageName, Amount, CloseDate, DealType, TrialEndDate, NextSteps, Account.Name, Account.AdminOrgId, Account.OrgId, Account.Domain FROM Opportunity WHERE OwnerId = '<userId>' AND IsClosed = false AND Account.Name LIKE '<name>%' AND (DealType = 'Paid Trial' OR TrialEndDate != null)`. More than one match, ask. No org id in either Account field, stop and report `org id missing in CRM`. Do not guess an org by name.

### 3. Pull

Substitute `<org_uuid>`, `<window_days>`, `<use_case_sample>`, and `<pilot_start>` from CRM and `policy.pilot_usage`. Use the configured read-only analytics adapter and warehouse. If it supports asynchronous execution, submit with that option. Submit every statement of the run before polling any. Keep the first-line marker comments intact. Exclude internal-domain roster and task rows. Keep organization filters on billing and query data as well as roster data. Preserve complete source results and page/partition receipts.

- `report` mode runs queries 1, 1b, 2, 3.
- `pdf` mode runs queries 1, 4, 5, plus 3 only when the narratives need a use-case sample.

Poll each handle to terminal success. In `report` mode a statement that errors or runs past `policy.pilot_usage.statement_timeout_minutes` prints `not available` with the reason for that section only. In `pdf` mode any failed statement stops the build.

### 4a. Report mode

Plain text per [references/pilot-usage-report-format.md](references/pilot-usage-report-format.md). Use cases: cluster the sample into at most five themes, each with a count and one short example verbatim. Skip file names, JSON, and single words. Then one line from `NextSteps` on what the buyer said they wanted.

### 4b. PDF mode

1. Pull CRM Contacts on the Account for display names. A seat with no Contact keeps the email local part.
2. Draft the review file per [references/pilot-usage-pdf-format.md](references/pilot-usage-pdf-format.md) into `policy.pilot_usage.pdf.output_dir`. Categories, task categories, display names, and every narrative are your drafts from the task titles and rows.
3. Show the drafts in chat, numbered, and wait. Set `approved: true` only after the user approves. Apply corrections to the file, not to the scripts.
4. Run the pipeline in `policy.tooling.scripts.pilot_usage_pdf`, in order: `assemble_pilot_usage_input.py`, `compute_pilot_usage_report.py`, `validate_pilot_usage_report.py`, `render_pilot_usage_report.py`, `print_pilot_usage_pdf.py`. Assemble and validate print status JSON; compute and render write their declared output files; print returns PDF inspection JSON. Stop on any non-zero exit or `"valid": false` and report the problem verbatim.
5. Inspect both rendered pages for clipped or overlapping text, then share the PDF in the thread. Outputs stay in `output_dir`. Nothing enters Project Files.

### 5. Close

One line. Pilot reported, mode, and `Nothing written`. In `pdf` mode add the credits used of granted and the PDF path.

### Refuse

Any CRM or warehouse write. Emailing or drafting outreach. Resolving an org by name match. Running more than the one named pilot. Printing query text or a query string over 120 characters anywhere, including the PDF. Setting `approved: true` before the user approves. Saving PDF, HTML, or JSON outputs to Project Files.

## Outputs and readiness

Save the pilot readout and source gaps in `output/{run-id}/01_review.md`, with
PDF artifacts in the configured run output directory. Complete the mode-specific
checks above, share the deliverable and record this read-only review through the
[run lifecycle](../run.md).

## Human check

Check the pilot scope, reconciled totals and use-case interpretations. In PDF
mode, approve the draft narratives and categories before building, then inspect
both pages before sharing.
