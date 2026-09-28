# Configure providers once

No CRM, mail, calendar, analytics, messaging or provisioning provider is required
by name. Map the selected tools into the logical contracts below. This template
ships instructions and local validators, not live connectors or credentials.

Private adapters.json contains version 2, mode, the reviewed policy SHA, capability
entries, field_mappings, state_mappings and data_contracts. Each capability records
status, provider, actual tool, contract and verified_at. Use a verified provider
name or `user-supplied-export` when appropriate. A string in configuration does not
establish tool availability or access; inspect the current tool schemas and readbacks.

| Capability | Contract to configure |
|---|---|
| crm.read | Identity, record/query reads, logical objects/fields, owner scope, pagination, errors and URLs |
| crm.write | Reverse field mapping, native types/states, fresh read, exact payload, create dedupe and independent readback |
| mail.read | Search/full-body reads, actual page tokens, message/thread IDs, recipients, sent direction and history limits |
| mail.draft | List/read/create unsent drafts, MIME/body format, selected reply parent, ID and independent readback; never send |
| calendar.read | Calendar identity, query scope, date bounds, page tokens, attendee IDs and start/end |
| transcripts.read | Meeting identity, account linkage, speaker/time provenance and full text; user notes are a labeled fallback |
| usage.read | API/database/file-to-roster/activity mapping, account/window, record grain, timezone, unit and completeness |
| handoff.post | Optional destination/recipients, duplicate search, exact message, returned ID and readback |
| provisioning.execute | Optional reviewed eligibility, payload, side effects, idempotency, polling, recovery and readback |
| pdf.render | Local Chromium binary and PDF inspection |
| web.read | Dated public source retrieval and links |

The core vocabulary uses Account, Opportunity, Contact, Task and Event as logical
objects. A provider may call them companies, deals, people, activities or meetings.
Map native names/types to these logical fields and reverse-map only exact approved
writes. No API schema, custom field suffix, query dialect or ID length is assumed.
See [the detailed data contract](../_shared/adapter-contract.md). Unsupported required
fields remain gaps, not guessed substitutes. Configure currency/revenue basis before
summing money, and stages/order/criteria as a consistent set.

Provider-specific examples may inform your private mapping: a reply draft may use
a parent message ID rather than a thread ID; calendars may have tokens or only a
known hard cap. Inspect the actual contract. Follow every page; split capped windows
only when that provider supports complete bounded queries. Unknown completeness
stays unknown even when a local result is empty.

## Configuration shape

Run `.venv/bin/python _system/scripts/setup.py requirements --workflow <name>` from the
repo root for the exact required keys. Add `--effect crm.write`, `--effect
mail.draft` or another supported effect to include its contract. The command uses
your private policy when present, otherwise the example. Conditional fields in
policy become required mapping keys for the workflows that consume them.

`field_mappings` maps logical object names to objects of logical field names and
nonempty native paths or reviewed expressions. `state_mappings` maps logical field
names to objects of logical values and native values. For example, the shape of
one partial mapping is:

```json
{
  "field_mappings": {"Opportunity": {"Id": "deal.id", "NextSteps": "deal.next_action"}},
  "state_mappings": {"Task.Status": {"open": "pending", "completed": "done"}}
}
```

This partial example cannot pass doctor. Supply every required key from
`requirements`, including stage keys and forecast categories for applicable
workflows. A baseline covers the standard procedure; additional fields selected
for a particular proposal also need verified mappings before that proposal.

`data_contracts` maps each capability to an object whose keys come from
`requirements`. Each value is a nonempty description of the actual mapping or
behavior, including limitations. For example, `crm.read` requires `identity`,
`queries`, `pagination`, `errors` and `types`; `crm.write` requires `payload`,
`preconditions`, `deduplication`, `readback` and `recovery`. Document field types,
nulls, currency/date semantics and transformations in these contracts.

Each capability's `provider`, `tool` and `contract` must be nonempty text;
`status` must be `configured` and `verified_at` a past or current ISO timestamp
with a UTC offset. Record actual verification times, not an invented readiness
stamp. Use `adapters.mode: configured` only after review and bind
`policy_sha256` to the reviewed policy bytes. There is no separate policy mode.
Doctor checks structure and local consistency, not whether these descriptions
are true. Confirm real schemas, permissions and bounded readbacks in this chat.

## Explicit evidence capture

Initialize `.venv/bin/python _system/scripts/run.py init <workflow>` and retain its printed external
path and started_at. Preserve actual request and response bytes, then prepare a
normalized JSON file with exactly input and output objects. A synthetic example:

```json
{
  "input": {"arguments": {
    "query_id": "owned-open", "source": "crm", "owner_id": "example-seller",
    "object": "Opportunity", "selection": "all_owned_open",
    "provider_query": "exact request as issued", "cursor": null
  }},
  "output": {"result": {
    "status": "success", "records": [], "total_count": 0, "next_cursor": null
  }}
}
```

An empty example is never live evidence. Capture each successful read page using:

```sh
.venv/bin/python _system/scripts/receipts.py capture --run <run> --call-id crm-001 \
  --raw-input <raw-request-file> --raw-output <raw-response-file> \
  --normalized <normalized-file> --provider <actual-tool-or-file-source> \
  --started-at <actual-offset-time> --completed-at <actual-offset-time>
.venv/bin/python _system/scripts/receipts.py verify --run <run>
```

Capture adds actual timestamps and the raw response reference, hashes all bytes and
refuses overwrite, stale/future times and symlinks. Preserve failed attempts and
errors too; never normalize an error into empty success. The source checker rejects
failed normalized reads. A resolved retry needs reviewed evidence of resolution;
keep original failures in raw evidence and disclose them, or retain a partial run.
Never discard an unresolved failure merely to pass a check.

The receipt verifier checks integrity and run binding; it cannot authenticate a
provider, validate a manual transformation's meaning or establish completeness
beyond the declared query. Review exact raw requests, field mappings, timestamps,
access filters and normalization. Stable query_id and selection persist across pages;
only actual cursors/native page requests change. Null next_cursor is terminal only
when the provider establishes it. total_count is the complete query count, not page
length; derive it only after verified terminal traversal when no native total exists.

For mail navigation/counts, preserve full-body envelopes separately and bind them
by provider_reference per the detailed contract. For pilot usage, use the same
receipts with source `usage` and the [pilot selections](../workflows/pilot-usage/references/data-contract.md).
Do not read Codex internal logs to reconstruct tool evidence.

After an approved effect, preserve exact payload, preimage, response and independent
readback. Local configuration or a reviewed flag does not replace approval in chat.
