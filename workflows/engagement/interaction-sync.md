# Interaction Sync

Turn one completed customer interaction into reviewed CRM updates and an unsent follow-up draft.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Query sketches use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

One call in, one set of numbered proposals out, writes only on exact approval. CRM is the record. Buyer-stated facts are quoted, not paraphrased into claims.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. In a hosted project, sync the reusable files first. Record the selected scope in the run request.

### 2. Find the interaction

- Named call or "log this call": use the configured transcript adapter and search by day, newest first, filtering on attendee domain or title.
- No recording: search the calendar for the meeting, tell the user `No transcript found.`, and build the log from what the user tells you plus the calendar description.
- Record: transcript meeting id, date, start and end, attendees with emails.

### 3. Extract

From the transcript take, with speaker attribution:
- Buyer-stated facts as short quotes, at most `policy.interaction.max_buyer_quotes`. Cost, incumbents, decision process, named stakeholders, timeline, requirements.
- Commitments by each side, with any dates spoken.
- Pricing or seat figures. Mark each `buyer_confirmed` or `seller_stated`.
- Call type per `policy.call_prep.call_type`, then its `policy.call_prep.expected_information` items now answered, partially answered, or still open.

### 4. Reconcile

1. Contacts by attendee email, then name. Unmatched external attendees become Contact-create proposals with the Account from the matched attendees' domain.
2. Account and open Opportunities. If several are open, ask which one before proposing. If none, say so and propose nothing on the Opportunity; creation is the user's call.
3. Opportunity Contact Roles for each matched attendee. Missing roles become proposals.
4. Open Tasks: `SELECT Id, Subject, ActivityDate, Description FROM Task WHERE IsClosed = false AND (WhatId = '<OppId>' OR WhoId IN (<ContactIds>))`. Mark each as tied to this call or unrelated.
5. Duplicate check: `SELECT Id, Subject, ActivityDate, Description FROM Task WHERE (WhatId = '<OppId>' OR WhoId IN (<ContactIds>)) AND ActivityDate = <date> AND TaskSubtype = 'Call'` and read Subject and Description for `policy.crm.call_marker`. A hit means the call is already logged. Report it, skip proposal A, and in B, C, and F propose only what that Task and the existing Next line do not already carry.

### 5. Propose

Number every proposal. One record per approval. Show the full payload, current value to new value.

- **A. Completed-call Task.** Status Completed, TaskSubtype Call, ActivityDate call date, WhoId primary external Contact, WhatId Opportunity (Account if none), OwnerId the seller. Description line 1 is the `call_marker`, then the note with `note_prefix`, attendees, the quotes, commitments, and open items.
- **B. Opportunity update.** `NextSteps` per `policy.pipeline.next_steps_format`. Propose `StageName` only when `policy.pipeline.stage_entry` for the target stage, or a `stage_rules` line, is met in the transcript; quote the criterion in one clause. Include any `policy.pipeline.required_fields` value stated on the call, marked buyer_confirmed or seller_stated. `Amount` only from a source in `policy.interaction.amount_source`. If the configured CRM validation rules require a source field when leaving an early stage, include its supported value in the same proposal. A blank required field without evidence blocks the move.
- **C. Follow-up Task.** Due the Next line date from B, Not Started, Subject names the awaited item, linked to the Contact and Opportunity. The Next line date in B is the buyer-stated date when the buyer owns the action, else today plus `policy.followup.default_next_date_days`.
- **D. mail follow-up draft.** Follow `policy.email_voice`. Reply in the existing thread when one exists. To the external attendees, cc the seller. Include links promised on the call. Below the draft, list `Suggested attachments`: every document, deck, benchmark, or case study mentioned on the call, with the speaker and whether a matching file exists in `policy.email_voice.collateral_path`. Attach only what the user approves; a file must exist there or the user supplies it. Never send.
- **E. Records.** Contact creates, Opportunity Contact Role adds, Contact Title fixes heard on the call.
- **F. Complete open Tasks.** One proposal per open Task tied to this call: Status Completed, Description prepended with a `note_prefix` line pointing at the verified call Task from A, or the existing duplicate-match Task when A is skipped. Unrelated open Tasks are listed, not proposed.

### 6. Apply

For each approval: fresh read, write, readback with the changed fields and record link. If the draft adapter returns no ID, confirm by listing drafts on the thread and reading the exact draft back. Report anything CRM rejects with the validation message and one corrected proposal.

### 7. Close

Summarize applied, skipped, and rejected in five lines or fewer. Recommend calling `close` if the user says the deal is won.

### Refuse

Sending email. Closed Won stage moves (route to `close`) or Closed Lost moves (route to `pipeline-review`). Deleting or merging records. Editing records not tied to this call. Inferring Amount or seats from booking forms. Saving transcripts or customer material to Project Files.

## Outputs and readiness

Save the deliverable and exact proposals in `output/{run-id}/01_review.md`; show the relevant readout in the conversation. Declare every source receipt and proposed artifact in its `artifacts` list. A read-only run has no effects. Readiness requires the checks above and explicit source gaps; unsupported effects stay withheld. Record the actual conversation review in `review.json`, and applied, pending, failed, or skipped effects in `02_result.json` through the shared run lifecycle.

## Human check

Review the scope, evidence and exact payloads. Approval covers only the listed effects and revision. Fresh reads and independent provider readbacks are required for external effects.
