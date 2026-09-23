---
type: workflow
command: sales-call-prep
mode: read
---
# sales-call-prep

Prepare a sourced brief for one sales call or a named calendar window.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, calendar, mail; transcripts and adoption optional.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Resolve the named call or calendar window. Use configured internal domains to identify external attendees. If there is no event, say so and prepare from the supplied account context.
2. Resolve Contacts by attendee email, then name and domain; read the Account, open Opportunities, and recent activity. Preserve ambiguity instead of picking among plausible deals. Separate calls and notes from long logged email threads.
3. Read the latest relevant email thread when CRM logs do not already supply it. Read prior transcripts through the configured adapter when available. Attribute buyer statements and commitments to the speaker and source.
4. Read an adoption adapter only if configured and authorized for this purpose. Its absence is a named gap, never inferred usage. Search dated public company and attendee information within policy.research.max_sources.
5. Infer the call type from evidence and compare it with policy.call_prep.expected_information. Produce the brief with current situation, buyer objectives, commitments, hypotheses, discovery gaps, suggested questions, and CRM issues. Cite facts and label hypotheses throughout.
6. End with the handoff to interaction-sync after the call. This workflow has no external effects.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested read-only deliverable, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Its effects list is empty.

## Human check
Verify the correct attendees, account and deal; distinguish buyer statements from hypotheses. Missing optional sources stay visible in the brief.
