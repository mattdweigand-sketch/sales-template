# Sales Call Prep

Prepare a sourced brief for one sales call or a named calendar window.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Collection requirements use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

Read-only. CRM is the record; everything else is evidence. Every fact in the brief names its source. Anything inferred is labeled `Hypothesis`. Never restate a hypothesis as fact in a later section.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. Make the reusable workspace files available through the configured host before starting. Record the selected scope in the run request.

### 2. Resolve the calls

- Named person or company: calendar search by name, `policy.tooling.calendar_lookback_days` behind to `policy.tooling.calendar_lookahead_days` ahead. If no event, prep from CRM and say `No meeting found on the calendar.`
- Window ("today", "tomorrow", "this week", "each of these"): calendar search over that range. Keep events with at least one attendee whose domain is not in `policy.identity.internal_domains`.
- Record per call: title, start, duration, link, external attendees with emails, internal attendees, booking-form text if present in the description.

### 3. CRM

Per call, in this order, batching where possible:
1. Contacts by attendee email. No match: search by name, then Account by email domain. Report unmatched attendees.
2. Account: Name, Website, Industry, NumberOfEmployees, Description, OwnerId.
3. Open Opportunities on the Account: Name, StageName, Amount, CloseDate, NextSteps. Also the most recent closed one if none are open.
4. Activity in the last `policy.call_prep.history_days` days on the Account and Contacts, `Subject, ActivityDate, Status, Description`, newest first. Separate notes/calls from logged email using adapter-mapped activity kinds and direction metadata. Logged emails are long; read only the newest one per attendee for the full thread. Note whether any completed live call exists.
5. Flag record problems you see (wrong Account name, Closed Lost while active, missing Contact) under `CRM notes`. Do not fix them here.

### 4. mail

Skip this step when the CRM email log in step 3 already contains the attendees' thread inside the history window. Otherwise search attendee addresses, at most `policy.tooling.mail_search_max_addresses` per call. Run `policy.tooling.scripts.mail_contact_stats <owner_email> <saved_outputs...> --only <addresses>` for counts and the newest thread. Read only the newest thread's messages for what was promised, asked, or sent.

### 5. Prior calls

Use the configured transcript adapter. Search the Account and attendee names over `policy.call_prep.history_days` days. Take: date, attendees, buyer-stated facts as short quotes, commitments by either side, open questions. If unavailable, write `Prior call transcripts not checked.`

### 6. Public research

Web search the company and each external attendee. Keep at most `policy.research.max_sources` dated sources per company: the configured topics from policy.research.topics. Person: current title, tenure, public statements. Cite each with a link and date. Drop anything you cannot date.

### 7. Call type and gaps

Infer the call type per `policy.call_prep.call_type`. State the type and the evidence for it. Discovery gaps are the items in `policy.call_prep.expected_information[type]` not established by any source. Write `not established` for each.

### 8. Write the brief

Read [references/sales-call-prep-brief-formats.md](references/sales-call-prep-brief-formats.md) and use the single-call or multi-call format. Return the brief itself, not a source list with commentary. End with `CRM notes` if any, then one line: `Say "log this call" after the meeting and I will hand off to interaction-sync.`

### Refuse

Writing to CRM, mail, or Calendar. Sending anything. Saving customer material to reusable workspace files.

## Outputs and readiness

Save the sourced brief and explicit coverage gaps in `output/{run-id}/01_review.md`
and show the brief in chat. Complete the checks above and record this read-only
review through the [run lifecycle](../run.md).

## Human check

Check the selected calls, source attribution, labeled hypotheses and discovery
gaps before using the brief.
