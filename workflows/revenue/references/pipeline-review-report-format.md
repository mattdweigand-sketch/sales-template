# Report format

The complete report appears in the final chat answer and `01_review.md` for both manual and configured scheduled runs. Preserve the template headings and field wording; use policy.reporting for amounts/dates and verified record links. Source field text remains verbatim. The full approved payload lives in the run's inputs.json; the comparison below may omit unchanged history.

## Approval and display rules

- Number only exact, supported changes. Flags, missing evidence and contradictions belong in Needs your input; never create a note merely to make a record approvable.
- Each next-step block uses Current next steps, Recommended next steps and Evidence. Normally compare exact first entries and state once that older history is omitted and unchanged. If proposing any history change, or showing a requested full field, show both complete fields and identify that exception. Empty fields display Empty.
- The write uses policy.pipeline.note_next_line and next_steps_format. Include an explicitly proposed factual history addition inside Recommended next steps; preserve all retained history. Follow next_steps_review for unresolved deadlines/owners. A field-only finding says `No next-step change proposed. <precise field question>`.
- Field contents are ordinary text with each stored line visually separate; no fences, inline code, quotations or boxes. Keep commentary outside field text. Evidence names the source, date, contact and supported fact, adding bullets only as needed. Use readable source links or returned IDs; never invent a URL.
- Calendar timestamps establish scheduling only: say scheduled or elapsed, attendance unverified unless attendance is supported. A Task receipt establishes its metadata, not an email-body summary. Use the checker's Account-and-Opportunity scope; discrepancies with source evidence block the affected proposal.

## Daily layout

Fences below delimit the template; do not render them in chat.

```text
# Pipeline review · <report date>

Only the latest stored entry is shown, with older history omitted and unchanged. Legacy `Next:` entries are reproduced as stored, not rewritten.

<N> open · <k> in scope · <r> reviewed · <f> flagged · **<p> proposed changes** · <b> need input · 0 written
<out-of-scope stages> excluded · <n> deals · <formatted sum>
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

## Exceptions and counts

- Repeat blocks with consecutive proposal numbers and unnumbered needs-input accounts. Recommendations are short action sentences; Current remains verbatim. Omit empty sections, Other fields and the legacy sentence when irrelevant. If no proposals exist, replace the approval question with `No CRM changes proposed.`
- A fresh rerun starts `Fresh rerun replaces the earlier review.` Identify superseded drafts. When redisplaying an applied review, state that Current is the review-time snapshot and recommendations were applied; keep the same headings and do not pretend historical values are fresh reads.
- Count distinct opportunities: in-scope k = reviewed r + skipped s + not-checked u, with disjoint statuses. z counts reviewed deals with no hygiene trigger; such a deal may still have an extended task_gap proposal. Flags, needs-input findings and supported proposals are separate counts.
- The coverage line describes the actual check. On failure use `Coverage incomplete · <specific missing checks>` and withhold affected proposals. Extended mode names its actual mail/calendar scope instead of claiming a daily inbox check. Keep full receipts in the run.
- Before posting, compare displayed fields with source and full effect payload, verify retained history, and confirm an actual supported difference. Reconcile counts to the original open snapshot. A scheduled/subject-only observation cannot support claimed discussion outcomes.

## Extended additions

Append the following to the daily sections. Include task_gap-only candidates under Record proposals, without relabeling them hygiene triggers. Approve each record proposal separately.

```text
## Rollup
<stage from policy.pipeline.stage_order> <n> · <formatted sum> | ...
<configured forecast category> <formatted sum> · ... · Unmapped <n>
Closing this quarter <n>, <formatted sum>. Later <n>, <formatted sum>.

## Since <comparison date>
- New / Stage / Close date / Closed lines, or No changes.

## Record proposals
A. <Account> CloseDate <old> → <new>. <Evidence and basis>
B. <Account> StageName <old> → <new>. <Entry criterion and evidence>
C. <Account> Task "<Subject>" due <date>, linked to <Contact>. <task_gap evidence>
D. <Account> StageName <old> → Closed Lost. <Silence or buyer-no evidence>
E. <Account> Amount <old> → <new>. <Buyer-confirmed or user-supplied evidence>

Approve each letter separately. Approve all covers numbered notes and field fills only.
```
