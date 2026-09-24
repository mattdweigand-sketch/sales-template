# Task Triage Speed Run

Review due CRM tasks, prepare contextual follow-ups, and apply approved changes.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), this procedure and the policy sections named below. In the [run lifecycle](../run.md), read Start/Prepare/Status for review; read Exact effects/Apply only when proposing or executing changes.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Collection requirements use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

You act as the seller in CRM and mail. CRM is the authority for Tasks and Contacts. mail and Calendar are evidence. Work in chat as plain text with numbered lists. No forms, tables, or cards. Reusable workspace files never hold customer data; keep review artifacts in the private run.

### 1. Load policy

From `_shared/policy.json`, load identity, followup, email_voice, crm and tooling. Load the relevant CRM/mail/calendar adapter sections and record the selected scope in the run request. Skip revenue, call-prep and public-research policy.

### 2. Collect the run

1. Get the current CRM user ID.
2. Query every open Task the user owns due today, overdue, or undated. No count or date cap unless the user sets one in this run.
   Required fields: Id, Subject, ActivityDate, Description, WhoId, WhatId, What.Name. Filter by owner, open state and due date at/before today or absent; order by due date through the configured adapter.
3. One Contact query over the distinct `WhoId` values: `Id, FirstName, Name, Email, Description, Account.Name`. A Task with no Contact or no email is grouped by step 4 like any other and its gap is listed under `CRM corrections needed`.
4. Report only the Tasks in this run. Never report total-queue or future-Task counts.

### 3. Gather evidence

1. mail: search Contact addresses at most `policy.tooling.mail_search_max_addresses` per call. On a timeout, retry once with a smaller batch.
2. Save complete paired `contact_history` receipts for the requested addresses and both directions. Run `policy.tooling.scripts.mail_contact_stats <owner_email> <saved_output_json...> --only <addresses> --calls <run>/calls --since <run-start>`. Use its counts and message IDs for navigation. Missing pages, classifications or limited history remain explicit; they cannot establish never-replied/cold status. Only an identified failed recipient establishes a bounce; automatic subjects and quoted addresses do not.
3. Calendar: for Tasks whose Subject or Description names a meeting, call, or session, run one calendar search from `policy.tooling.calendar_lookback_days` behind today to `policy.tooling.calendar_lookahead_days` ahead, with the account names as queries. An invitation establishes scheduling only. Use attendance evidence or a reviewed source to establish that a meeting was held or moved.
4. Existing drafts: list drafts once. Match `thread_id` against the thread ids from step 2. Read any draft needed to verify its recipients and intended follow-through; preserve held items even before that inspection is complete.
5. Read each Task Subject and Description for the intended ask.
6. Prior email body: for every Task that may get a draft, read the full body of the user's newest outbound message in the thread (the message id from step 2) and the newest inbound reply if one exists. Note the specific claim, offer, or question it made. Drafting from Task notes alone is not allowed.

### 4. Group

Establish the facts from the selected Task's actual thread, not the Contact's unrelated newest thread. A substantive reply or verified held meeting makes the Contact active; incomplete relationship evidence is unknown, not cold. Interpret reply meaning, meeting attendance and the intended ask with their full sources.

Save `triage-input.json` with a `tasks` array, bound as `inputs.json`'s `sources.triage`. Each row contains `task_id`, `mailbox`, `thread_id`, `existing_draft`, `mail_complete`, `relationship` (active/cold/unknown), `last_sent_at`, `last_reply_at`, `held_meeting_at`, `meeting_moved`, `internal_prep`, `unanswered_count`, `recipient` (confirmed/unconfirmed/unknown), `cooldown_until`, `channel` (email/linkedin_only/unknown), `bodies_complete`, and `source_refs`. Timestamps are offset-aware or null; dates are ISO; booleans/counts may be null when unknown. Null message dates mean confirmed absence only with complete supporting history. Source paths are relative to this run. Add `contact_email` when multiple external correspondents make the selected thread ambiguous; readiness verifies the selected person and message facts against saved mail.

Run `policy.tooling.scripts.triage_check <run>/triage-input.json --policy _shared/policy.json --as-of <run-start>`. It calculates groups and dates; it does not certify these interpreted facts. Existing drafts are held first. Remaining Tasks use first-match order:

1. **Reply received / manual response.** Verified newer substantive reply/held meeting, moved meeting or internal prep. Review Complete versus a new date; the helper does not choose. With complete history, substantive inbound and no outbound is manual response.
2. **Recycle decisions.** Established cold Contact, complete history and the configured unanswered threshold. Offer Push or Recycle. This retains precedence over timed Hold; active/unknown Contacts never recycle.
3. **Hold.** Recent-send window, future cooldown, unconfirmed recipient, LinkedIn-only, or a required unknown. No draft. The helper supplies the latest known timed release date; unresolved recipient/channel/evidence has no invented expiry.
4. **Draft email recommended.** Confirmed recipient and full selected-thread context, no existing draft or earlier condition. The helper supplies the active/cold follow-up date.

All offsets are calendar days in `policy.identity.timezone`. A missing CRM Contact alone is a correction, not a hold when identity is independently verified. Preserve every Task, including held and needs-input items.

### 5. Full readout

One message, all groups in the order above, every Task listed. Open with `**N Tasks in this run.** Nothing created or changed.` Line format:
`n. [Account · FirstName]({record_url}) · <action or date> · <reason>`

Number Tasks continuously across groups. End with `CRM corrections needed` if any, then `Walk the sections?`

### 6. Section walk

After the readout, walk the groups in order. For each group: show the exact bulk change, take one approval, execute, read back, report, then move to the next group. The user can say `skip` to pass a group or give changes by number.

1. **Reply received / manual response.** One map of Task to Complete or new date, each row with its note line. One approval.
2. **Recycle decisions.** Ask Push or Recycle per Contact, or one choice for all. Then show each email and Task ID and require explicit approval of those exact choices; an existing unambiguous approval in this run is sufficient.
3. **Hold.** One map of the proposed date moves. Keep-today rows need no write and are not listed.
4. **Draft email recommended.** For every draft show one line `Prior email: <date>, <one-clause summary of its claim or ask>`, then exact To, Subject, and body. Approve by number or `all`. Create and verify, then show one map moving those Tasks to the proposed date. One approval. A failed or uncertain draft withholds the related Task move; reconcile its outcome before retrying.
5. **CRM corrections.** One record per approval, per step 9.

Approval covers only the listed records and named fields. A change to one row does not reopen an approved row.

### 7. Drafts

Follow `policy.email_voice`. Every follow-up continues the prior email read in step 3.6. It names or restates one specific claim, offer, or question from that email and moves it forward with one new fact or a sharper version of the same ask. A question the prior email did not set up is not a follow-up. Write for a cold read. Restate the referenced point in plain words instead of pointing at it. Short sentences, one idea each. If the ask is not clear in five seconds without the thread, rewrite. Reply in the existing thread when one exists. Use the adapter's supported reply-thread operation. Verify the exact recipients independently. Inspect automatically quoted text. If it contains internal notes, flag `Quoted internal note: remove before sending` in the readout. Before approval, add each exact draft to its triage row as `draft` with `to`, `cc`, `bcc`, `subject`, `body`, and `attachments`, then rerun the helper. Share one draft candidate only when mailbox, thread and all draft fields are identical; conflicting recipients or asks on one thread need reconciliation. Every Task stays accounted for. After creating, list drafts and read the new one back; confirm recipient, subject, and body match. Report `Draft ready`. Never send.

### 8. Writes

- Every Task change carries a note: prepend one line to Task `Description` using `policy.crm.note_prefix`, stating the change and the reason. Existing text stays below it. Show the note text in the approval map.
- Date move: Task `ActivityDate` plus the note.
- Complete: Task `Status` = `Completed` plus the note.
- Recycle: complete the Task with its note, then prepend `policy.crm.cooldown_marker` to Contact `Description`, keeping existing text.
- Re-read each record immediately before writing. If any field the proposal relies on changed, withhold that effect and revise its proposal per the shared rules.
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
