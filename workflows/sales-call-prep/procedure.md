---
cadence: one-off
reads: _shared/policy.yaml (call_prep, crm, identity, pipeline, research, tooling), _shared/rules.md, setup/adapters.md, references/
writes: nothing
next: CRM and chat carry business state
---

# Sales Call Prep

Prepare a sourced brief for one sales call or a named calendar window.

Apply rules#read_only_skills.

## Load / Skip

Read setup/adapters.md and the private policy blocks below. Start per
rules#run_start. Follow rules#approval and rules#write_protocol for effects.
Read only this procedure and the references it names; skip unrelated workflows.
All record and field names here are normalized logical names, mapped through the
configured adapter. Missing capabilities block only dependent steps.

## Process

Read-only. CRM is the record; everything else is evidence. Every fact in the brief names its source. Anything inferred is labeled `Hypothesis`. Never restate a hypothesis as fact in a later section.

### 1. Load policy

From `_shared/policy.yaml`, load identity, call_prep, research, tooling and crm.record_url; load the relevant source sections of `_shared/adapters.json`. Record the selected scope in the run request. Skip revenue and drafting policy.

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

Skip this step when the CRM email log in step 3 already contains the attendees' thread inside the history window. Otherwise search attendee addresses, at most `policy.tooling.mail_search_max_addresses` per call. Save complete paired receipts and run `policy.tooling.scripts.mail_contact_stats <owner_email> <saved_outputs...> --only <addresses> --calls <run>/calls --since <run-start>` for counts and thread navigation. Limited history stays labeled; it cannot establish never-replied status. Read the complete relevant messages for what was promised, asked, or sent.

### 5. Prior calls

Use the configured transcript adapter. Search the Account and attendee names over `policy.call_prep.history_days` days. Take: date, attendees, buyer-stated facts as short quotes, commitments by either side, open questions. If unavailable, write `Prior call transcripts not checked.`

### 6. Public research

Web search the company and each external attendee. Keep at most `policy.research.max_sources` dated sources per company: the configured topics from policy.research.topics. Person: current title, tenure, public statements. Cite each with a link and date. Drop anything you cannot date.

### 7. Call type and gaps

Infer the call type per `policy.call_prep.call_type`. State the type and the evidence for it. Discovery gaps are the items in `policy.call_prep.expected_information[type]` not established by any source. Write `not established` for each.

### 8. Write the brief

Read [references/brief-formats.md](references/brief-formats.md) and use the single-call or multi-call format. Return the brief itself, not a source list with commentary. End with `CRM notes` if any, then one line: `Say "log this call" after the meeting and I will hand off to interaction-sync.`

### Refuse

Writing to CRM, mail, or Calendar. Sending anything. Saving customer material to reusable workspace files.

## Outputs and readiness

Save the sourced brief and explicit coverage gaps in `<run>/outputs/review.md`
and show the brief in chat. Complete the checks above and record this read-only
review through the [shared rules](../../_shared/rules.md).

## Human check

Check the selected calls, source attribution, labeled hypotheses and discovery
gaps before using the brief.
