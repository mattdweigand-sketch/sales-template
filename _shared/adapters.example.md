---
type: adapter-configuration
status: unconfigured
---
# Adapter configuration

Copy to adapters.md and fill only the adapters needed by a workflow.
No credentials belong in this file. An adapter is a mapping to tools the host
already exposes; this repository does not ship an authenticated connector.

## CRM
Provider and tools: unconfigured.
Identity lookup; account/domain resolution; owner and open-deal query: unconfigured.
Contact, Task, Event and Opportunity field/status mapping and reverse mapping: unconfigured.
Activity kind and inbound/outbound direction from native metadata: unconfigured.
Amount currency and revenue basis; any conversion source/date: unconfigured.
Stable record URLs, pagination and complete-result indication: unconfigured.
Allowed write operations and fresh-read/readback tools: unconfigured.
Validation messages, task duplication keys and note history format: unconfigured.

## Mail and calendar
Search, paging, sent-message proof, read-message and calendar tools: unconfigured.
Draft creation, draft identity lookup and independent readback: unconfigured.
Internal domains come from policy.identity; do not repeat them here.

## Optional capabilities
Transcript retrieval and speaker attribution; customer product/service footprint; pilot scope, participant IDs, activity grain, metric unit, precision and optional allocation definitions.
Each enabled adapter must name its tool, input mapping, output fields,
completeness criteria, permitted audience and verification read. Keep disabled
capabilities unavailable until configured and tested with synthetic data.

## Saved-source interface
Read [adapter-contract.md](adapter-contract.md). Record the normalization mapping,
raw receipt location, complete-page evidence and source timezone for each adapter.
For coverage, identify the actual unfiltered owned-open query and scoped secondary
queries. For pilot analytics, map the roster, activities and optional allocations from
the analytics contract. Preserve verified scope filters, units, reporting timezone,
window and terminal success for database, API or export sources alike.
