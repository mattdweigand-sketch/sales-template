---
type: workflow
command: forecast-weekly
mode: write
---
# forecast-weekly

Build an evidence-backed quarterly forecast and propose explicit CRM corrections.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, mail, calendar.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Resolve the quarter, configured targets and CRM amount basis. If no target is configured, omit target-gap arithmetic and report it as missing.
2. Read booked deals, in-quarter open deals and configured next-quarter candidates. Retrieve their Contacts, Tasks and Events. Retain original scope counts.
3. Read and page buyer email and calendar evidence for each deal in policy.forecast.evidence_scope. Record coverage explicitly. Fresh communication can inform the forecast while producing a separate CRM correction proposal.
4. Apply the team's documented commit, upside, excluded and pull-in definitions in policy.forecast. Cite why each deal qualifies or the condition it fails. Report missing bucket definitions instead of inventing them. Every in-scope deal appears exactly once in a forecast bucket.
5. Calculate booked plus commit, upside, target gap when configured, and a ranked path to target. Show pull-ins separately; do not double-count them in the forecast or upside buffer. Reconcile totals to underlying deals.
6. Present the forecast, blockers, buyer-owned next dates, coverage gaps and exact CRM corrections. Forecast-category synchronization is a separately approved effect. Route stage or amount changes to pipeline-review and signed close work to close.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Check that all deals and sources are accounted for, bucket criteria match evidence, and totals reconcile. Reviewing the forecast does not authorize its CRM proposals.
