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
Contact, Task, Event and Opportunity field mapping: unconfigured.
Stable record URLs, pagination and complete-result indication: unconfigured.
Allowed write operations and fresh-read/readback tools: unconfigured.
Validation messages, task duplication keys and note history format: unconfigured.

## Mail and calendar
Search, paging, sent-message proof, read-message and calendar tools: unconfigured.
Draft creation, draft identity lookup and independent readback: unconfigured.
Internal domains come from policy.identity; do not repeat them here.

## Optional capabilities
Transcript retrieval and speaker attribution; organization adoption lookup; pilot analytics grain and metric definitions; signed-close fields; approved billing, provisioning and handoff paths.
Each enabled adapter must name its tool, input mapping, output fields,
completeness criteria, permitted audience and verification read. Keep disabled
capabilities unavailable until configured and tested with synthetic data.

## Saved-source interface
Read [adapter-contract.md](adapter-contract.md). Record the normalization mapping,
raw receipt location, complete-page evidence and source timezone for each adapter.
For coverage, identify the actual unfiltered owned-open query and scoped secondary
queries. For pilot SQL, map all five logical views and preserve organization
filters. For setup provisioning, describe the exact payload, overwritten terms,
automatic invitations, terminal success criteria and recovery behavior.
