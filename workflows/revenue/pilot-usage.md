---
type: workflow
command: pilot-usage
mode: read
---
# pilot-usage

Summarize one pilot's adoption from a configured analytics source.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, analytics.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Resolve one pilot and its agreed dates from CRM and user-provided evidence. Require an explicit analytics adapter in _shared/adapters.md; otherwise return a precise missing-adapter finding.
2. Read only the agreed scope and permitted metrics. Record the data-through date, reporting window, metric definitions, grain and units. Check snapshot completeness and organization-to-account mapping before computing trends.
3. Separate enabled seats, active users, activity, credits or spend, and task categories. Distinguish these adoption measures from business outcomes. Never infer ROI from activity alone.
4. Produce a sourced review with totals, time trend, methodology, limitations and recommended pilot questions. Identify named users or query examples only when the configured audience and privacy rules permit them.
5. A requested PDF is rendered from the human-reviewed content with the team's own approved assets. The template imposes no private brand fonts, proprietary SQL schema, or fixed internal warehouse. Verify the rendered artifact before delivery.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested read-only deliverable, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Its effects list is empty.

## Human check
Check reporting dates, metric definitions, totals, audience permissions and the distinction between adoption and business results. No CRM write belongs to this workflow.
