# Report format

Post the complete report once in the final chat answer, not only in commentary, a notification, a file, or a linked thread. Preserve the same review and full write payloads in the run artifact. This is the fixed template for manual and configured scheduled runs. Preserve its heading names, order, numbering, spacing, and plain field text; substitute run data rather than redesigning the layout. Record links use `policy.crm.record_url`. Friday sections appear only on Friday.

## Approval boundary

A flag is a review finding, not automatically a proposed write. Number only exact, evidence-supported changes. Put `no action derivable`, unresolved contradictions, and unsupported field values in **Needs your input**, outside the approval batch. Do not invent a history note to make a flagged record approvable.

Use exactly three sections per next-steps proposal: Current next steps, Recommended next steps, and Evidence. For a next-step-only change, show the exact current first entry and the exact proposed next-step sentence, not the unchanged history twice. State once above the proposals that the comparison shows first entries only and existing history stays unchanged. The write payload must still retain all history per `policy.pipeline.next_steps_format`. If proposing a history change, or the user asks for the full field, show the complete current and proposed fields instead. Preserve wording, punctuation, dates, and line order. Never replace exact text with an action summary or Unchanged. If the current field is empty, show Empty rather than inventing stored content.

Include any proposed new history entry within Recommended next steps, not in a separate History section. Use the current `policy.pipeline.note_next_line` for the actual CRM next-step wording, not merely for the report's presentation. Preserve existing entries per `next_steps_format`. Distinguish the action's due date from the entry's written date and CloseDate. Follow `next_steps_review` when the checker cannot resolve a date or owner. When a fresh CRM read supersedes an earlier draft, explicitly identify the outdated draft and the evidence for the revised recommendation. For a redisplay of an approved review, retain these same three headings and state once at the top that Current refers to the review-time snapshot and recommendations have already been applied. Do not introduce Before/After headings, rewrite historical snapshots into the new format, or imply those snapshots are fresh live reads.

Calendar start/end times prove scheduling, not attendance or outcomes. Never describe an upcoming or ongoing event as held. If the only evidence is a calendar entry, say `scheduled` or `elapsed, attendance unverified`. A Task subject supports its title, direction, activity date, and contact only, not a summary of the email body.

Use the checker's Account-and-Opportunity activity scope for last touch, not a separate Opportunity-only lookup. Show the source record for each trigger and proposed factual addition. If sources disagree with the checker, withhold the affected proposal and identify the discrepancy rather than treating its output as proof.

## Daily layout

The example fences delimit the template only; do not render them in chat.

```text
# Pipeline review · <M/D/YY>

Only the latest stored entry is shown, with older history omitted and unchanged. Legacy `Next:` entries are reproduced as stored, not rewritten.

<N> open · <k> in scope · <r> reviewed · <f> flagged · **<p> proposed changes** · <b> need input · 0 written
S0/S1 excluded · <n> deals · $<sum>
Coverage complete · Inbox, Calendar and contact domains checked

## Proposed changes

1. <Account link>

### Current next steps
<exact current first next-step entry>

### Recommended next steps
<exact short next-step sentence using policy.pipeline.note_next_line>

### Evidence
- <short dated explanation with supporting source link>

- **Other fields** <field, old → new, evidence; omit if none>

## Needs your input

<Account link>

### Current next steps
<exact current first next-step entry>

### Recommended next steps
No proposal yet. <one precise question needed to propose a change>

### Evidence
- <short dated explanation with supporting source link>

<z> reviewed deals had no trigger · <s> skipped · <u> not checked

**Approve <number range>, individual numbers, or skip?**
```

Repeat each account block unchanged in structure. Number only supported proposals, consecutively; needs-input accounts remain unnumbered. Omit stage, Amount, and CloseDate from daily account headings. Recommendations are one short action sentence, not a recap; Current remains verbatim even when longer or in legacy format. Use one compact evidence bullet by default, adding another only when necessary to support the change. No extra explanatory paragraphs per account.

For a fresh rerun, prefix the opening paragraph with `Fresh rerun replaces the earlier review.` For a field-only finding, use `No next-step change proposed. <precise field question>` under Recommended next steps. Omit the legacy-format sentence if no displayed entry uses it. When complete fields are required by the approval boundary above, identify those accounts in the opening paragraph and show their full fields instead of claiming all history is omitted and unchanged. If no proposals exist, omit the approval question and state `No CRM changes proposed.` Never number a needs-input record to fill the template.

Count distinct opportunities: `k` is in scope, `r` has all required checks completed, `s` is explicitly skipped within scope, and `u` has unresolved required checks. These three review statuses are disjoint and `k = r + s + u`. Count `z` directly from reviewed deals with no trigger; flags on partially checked deals must not reduce it. Keep flagged deals, needs-input findings, and supported proposed changes separate. Incomplete checks never count as reviewed.

The coverage header summarizes the actual successful coverage check, not an assumption. On incomplete coverage, replace it with `Coverage incomplete · <specific missing checks>` and withhold affected proposals. Keep the full checker receipts in the active run, not the report. Friday uses its actual mail and Calendar coverage instead of the weekday inbox claim.

Use only Current next steps, Recommended next steps, and Evidence as per-deal section headings. Render the field contents as ordinary plain text beneath each heading, keeping every stored line visually separate and preserving its wording and punctuation. Do not use fenced or indented code blocks, inline code, blockquotes, or text boxes in the report. Keep commentary and evidence outside the field text so they cannot be mistaken for part of the write. Use short evidence bullets naming the source, activity date, contact when known, and supported fact. Include last-touch direction and subject when relevant. Prefer readable source links to raw IDs; when no source URL is available, use a readable description with the returned record ID, never an invented link. Include enough evidence to support every changed clause without repeating it.

Omit empty top-level sections and Other fields when absent. Keep numbered proposals visually separate with a blank line. Never present a no-action finding as writable next-step text.

## Friday additions

After the daily sections, preserve these sections and separate approvals.

```text
## Rollup
S0 <n> · $<sum> | S1 ... | S5 <n> · $<sum>
Commit $<sum> · Best Case $<sum> · Pipeline $<sum> · Omitted <n>
Closing this quarter <n>, $<sum>. Later <n>, $<sum>.

## Since <last Friday M/D>
- New / Stage / Close date / Closed lines, or No changes.

## Record proposals
A. <Account> CloseDate <old> → <new>. <Evidence and basis>
B. <Account> StageName <old> → <new>. <Entry criterion and evidence>
C. <Account> Task "<Subject>" due <M/D>, linked to <Contact>. <task_gap evidence>
D. <Account> StageName <old> → Closed Lost. <Silence or buyer-no evidence>
E. <Account> Amount <old> → <new>. <Buyer-confirmed or user-supplied evidence>

Approve each letter separately. Approve all covers numbered notes and field fills only.
```

## Before posting

- Check each proposed addition against its source, including meeting times. Do not claim discussion outcomes from invitations or email subjects.
- Confirm the actual difference from current CRM. No difference means no write.
- Compare Current next steps against the source and Recommended next steps against the intended write payload and current policy formats. Verify retained history is unchanged in the payload even when omitted from the compact comparison. Show complete fields whenever history changes are proposed. Do not add unsupported history merely to fill the template.
- Count supported proposals separately from flags and needs-input records. A blocked record is not awaiting approval.
- Close with open, in scope, reviewed, flagged, proposed, written, skipped, and not checked counts. Retain the original open count and reconcile review statuses to the in-scope count.
- Compare the rendered report to the Daily layout before posting. All displayed accounts have the three exact headings in order, Current contains the first stored entry unless complete fields are required by the approval boundary above, and each recommendation matches the intended write. The final answer must contain the report itself, not a completion summary.
