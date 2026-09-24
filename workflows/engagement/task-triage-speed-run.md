# Task Triage Speed Run

Review due CRM tasks, prepare contextual follow-ups, and apply approved changes.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Query sketches use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

You act as the seller in CRM and mail. CRM is the authority for Tasks and Contacts. mail and Calendar are evidence. Work in chat as plain text with numbered lists. No forms, tables, or cards. Reusable Project Files never hold customer data; keep review artifacts in the private run.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. In a hosted project, sync the reusable files first. Record the selected scope in the run request.

### 2. Collect the run

1. Get the current CRM user ID.
2. Query every open Task the user owns due today, overdue, or undated. No count or date cap unless the user sets one in this run.
   `SELECT Id, Subject, ActivityDate, Description, WhoId, WhatId, What.Name FROM Task WHERE OwnerId = '<userId>' AND IsClosed = false AND (ActivityDate <= TODAY OR ActivityDate = null) ORDER BY ActivityDate`
3. One Contact query over the distinct `WhoId` values: `Id, FirstName, Name, Email, Description, Account.Name`. A Task with no Contact or no email is grouped by step 4 like any other and its gap is listed under `CRM corrections needed`.
4. Report only the Tasks in this run. Never report total-queue or future-Task counts.

### 3. Gather evidence

1. mail: search Contact addresses at most `policy.tooling.gmail_search_max_addresses` per call. On a timeout, retry once with a smaller batch.
2. When the platform saves a result to a file, read only the script output. Run `policy.tooling.scripts.gmail_contact_stats <owner_email> <saved_output_json...> --only <addresses>` against the saved tool outputs. It prints per-address sent count, last sent date, last inbound date and type (`substantive`, `ooo`, `bounce`, `calendar`), unanswered count since the last substantive reply, and the newest non-bounce message and thread id. A `bounce` type means recipient unconfirmed.
3. Calendar: for Tasks whose Subject or Description names a meeting, call, or session, run one calendar search from `policy.tooling.calendar_lookback_days` behind today to `policy.tooling.calendar_lookahead_days` ahead, with the account names as queries. Use it to decide whether the meeting happened or moved.
4. Existing drafts: list drafts once. Match `thread_id` against the thread ids from step 2. Read a draft only when its thread id is unmatched and it is a new message.
5. Read each Task Subject and Description for the intended ask.
6. Prior email body: for every Task that may get a draft, read the full body of the user's newest outbound message in the thread (the message id from step 2) and the newest inbound reply if one exists. Note the specific claim, offer, or question it made. Drafting from Task notes alone is not allowed.

### 4. Group

A Contact is **active** when the thread holds a substantive inbound reply or a meeting with that Contact. Otherwise it is **cold**.

An existing draft is shown as a held item, with its thread and intended follow-through; do not silently drop the Task or create a duplicate. Unknown mail coverage prevents recipient confirmation and recycle decisions. Assign each remaining Task to one group, first match wins:

1. **Reply received / manual response.** A substantive reply or a meeting with the Contact is newer than the seller's last sent email, the meeting moved, or the Task is internal prep. Propose Complete or a new date with a one-clause reason.
2. **Recycle decisions.** Cold Contact and unanswered count is at least `policy.followup.recycle_after_unanswered`. Active Contacts never recycle. Offer Push (move `policy.followup.cooldown_days`) or Recycle (complete the Task, write the Contact cooldown marker).
3. **Hold.** the seller sent within the hold window with no reply (`policy.followup.sent_mail_hold_days_cold` for cold, `policy.followup.sent_mail_hold_days_active` for active), a future cooldown marker is on the Contact Description, recipient unconfirmed (no address the seller has sent to without a bounce, or last inbound type `bounce`; a missing Contact record alone is a CRM correction, not a hold), or the only channel is LinkedIn. Propose a date or Keep today. No draft.
4. **Draft email recommended.** Confirmed recipient, no existing draft. Propose one draft and a date of today plus `policy.followup.next_date_days_active` or `policy.followup.next_date_days_cold`.

### 5. Full readout

One message, all groups in the order above, every Task listed. Open with `**N Tasks in this run.** Nothing created or changed.` Line format:
`n. [Account · FirstName]({record_url}) · <action or date> · <reason>`

Number Tasks continuously across groups. End with `CRM corrections needed` if any, then `Walk the sections?`

### 6. Section walk

After the readout, walk the groups in order. For each group: show the exact bulk change, take one approval, execute, read back, report, then move to the next group. The user can say `skip` to pass a group or give changes by number.

1. **Reply received / manual response.** One map of Task to Complete or new date, each row with its note line. One approval.
2. **Recycle decisions.** Ask Push or Recycle per Contact, or one choice for all. Then show each email and Task ID and require explicit approval of those exact choices; an existing unambiguous approval in this run is sufficient.
3. **Hold.** One map of the proposed date moves. Keep-today rows need no write and are not listed.
4. **Draft email recommended.** For every draft show one line `Prior email: <date>, <one-clause summary of its claim or ask>`, then exact To, Subject, and body. Approve by number or `all`. Create and verify, then show one map moving those Tasks to the proposed date. One approval.
5. **CRM corrections.** One record per approval, per step 9.

Approval covers only the listed records and named fields. A change to one row does not reopen an approved row.

### 7. Drafts

Follow `policy.email_voice`. Every follow-up continues the prior email read in step 3.6. It names or restates one specific claim, offer, or question from that email and moves it forward with one new fact or a sharper version of the same ask. A question the prior email did not set up is not a follow-up. Write for a cold read. Restate the referenced point in plain words instead of pointing at it. Short sentences, one idea each. If the ask is not clear in five seconds without the thread, rewrite. Reply in the existing thread when one exists. Use the adapter's supported reply-thread operation. Verify the exact recipients independently. Inspect automatically quoted text. If it contains internal notes, flag `Quoted internal note: remove before sending` in the readout. After creating, list drafts and read the new one back; confirm recipient, subject, and body match. Report `Draft ready`. Never send.

### 8. Writes

- Every Task change carries a note: prepend one line to Task `Description` using `policy.crm.note_prefix`, stating the change and the reason. Existing text stays below it. Show the note text in the approval map.
- Date move: Task `ActivityDate` plus the note.
- Complete: Task `Status` = `Completed` plus the note.
- Recycle: complete the Task with its note, then prepend `policy.crm.cooldown_marker` to Contact `Description`, keeping existing text.
- Re-read each record immediately before writing. If its date or status changed since the proposal, skip it and say so.
- Read every changed record back, including `Description`. Report `Verified in CRM` only after readback. Report an unverified write as pending. A failed row does not block other rows.

### 9. CRM corrections

Last group of the walk, for Tasks whose evidence shows a wrong or missing record. Allowed: create a Contact; update Contact `Email`, `Title`, or `AccountId`; update Task `WhoId`; replace only the person's name in Task `Subject`. Read [references/task-triage-speed-run-crm-corrections.md](references/task-triage-speed-run-crm-corrections.md) before proposing any of these.

### 10. Close

List: drafts created (unsent), Tasks completed, Tasks moved, Contacts recycled, CRM corrections applied, Tasks left for manual follow-through with reasons. End with `No emails sent.`

### Refuse

Sending mail. Deleting or merging any record. Bulk updates outside the approved maps. Financial fields. Opportunity edits. Contact `OwnerId` changes without a separate explicit approval.

## Outputs and readiness

Save the grouped readout, exact task changes and draft proposals in
`output/{run-id}/01_review.md`; show the full readout in chat. Complete the checks
above, name source gaps and use the [run lifecycle](../run.md) for review and effects.

## Human check

Review each section for task disposition, follow-up context, recipients and
exact draft or CRM changes before approving its effects.
