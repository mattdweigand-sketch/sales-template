# Close

Review a signed opportunity's close and track approved downstream handoff effects.

## Load / Skip

- Load [shared rules](../../_shared/rules.md), [run lifecycle](../run.md), the configured policy and adapters, and this procedure.
- Read [adapter data contract](../../_shared/adapter-contract.md) only for the sources used in this run. Query sketches use logical field names; map them through the adapter before calling a provider.
- Load the linked reference only at its named step. Keep raw source receipts and derived artifacts in this run.
- Skip sibling workflows, other runs, unrelated accounts, and unused adapter sections. Missing capabilities are named gaps or block their dependent effects.

## Process

One opportunity in, Closed Won verified, downstream done or handed off with a named owner. CRM is the record. The signed agreement is the authority for terms. Writes happen only on approval in this thread, one record per approval.

### 1. Load policy

Read the configured `_shared/policy.json` and `_shared/adapters.md`. In a hosted project, sync the reusable files first. Record the selected scope in the run request. Consult the configured CRM schema and validation guide when a validation message needs interpreting. Missing guidance is a gap, not permission to invent a value.

### 2. Resolve

`/close <Opportunity URL or Id>`. No opportunity: ask. Read [references/close-fields.md](references/close-fields.md) and query every field it lists on the Opportunity, its Account, line items, and Contact Roles. Read the Account's other Opportunities and the Account's `ParentId`.

### 3. Signature evidence

Closed Won needs one item from `policy.close.signature_evidence`. Quote the field and value or the user's words. Without it stop and say `No signature evidence.` A call, a verbal yes, a booking form, or a sent order form is not evidence.

### 4. Path

Read [references/close-paths.md](references/close-paths.md). Pick one path and state the fact that selected it. An API or other product type without a configured close flow blocks writes; collect the missing flow requirements.

### 5. Preflight

Compare each [references/close-fields.md](references/close-fields.md) term field to the agreement. Three outcomes, listed by field:

- Matches: no proposal.
- Blank, value in the agreement or on the record: proposal.
- Blank, no source: ask. A validation failure is never permission to invent a value.

A record value that contradicts the agreement is reported, and the proposal moves the record to the agreement, never the reverse. A billing interval other than `policy.close.terms_default.billing_interval` needs a Deal Desk approval link from `policy.close.deal_desk_channel` or the user's confirmation, quoted. Show the pilot's actual charge next to its annualized Amount per `policy.close.price_books`.

### 6. Propose

Numbered, one record per approval, current value to new value.

- **A0. Setup trial.** Only when the Account has no org UUID, per `policy.close.no_org_rule`. Read [references/close-setup-trial.md](references/close-setup-trial.md). One Opportunity update per `policy.close.setup_trial`, after explicit approval of the exact payload and disclosed invitation or provisioning side effects. Verify, then A. Declined or failed: propose E, hold A.
- **A. Stage.** `StageName` Closed Won, `CloseDate` = signature date. Skip when already Closed Won and say `Closed Won on <date> by <source>`. Blocked until A0 verifies when it applies.
- **B. Win fields.** `ClosedWonNotes` and `UseCases`, each a new line prepended per `policy.crm.note_prefix`, at most `policy.close.win_note_max_chars`, quoting the buyer where possible. Plus any term field from step 5, including every `policy.close.setup_trial.restore_after` field after A0. `NextSteps` per `policy.pipeline.next_steps_format` with the onboarding action. Never `NextStep`.
- **C. Account.** `BillingEmail`, `BillingPointOfContact`, `OrgId` and `AdminOrgId` from a system source only, `BecameACustomerOn` = CloseDate, `CustomerType`.
- **D. Contact Roles.** Signer and admin on the Opportunity when missing.
- **E. Operations handoff.** Only when the path or a downstream status in `policy.close.handoff_when` calls for it. Exact text per the template in [references/close-paths.md](references/close-paths.md), to `policy.close.ops_channel`, mentioning `policy.close.ops_owners`. Post only after explicit approval of the exact message and destination; existing unambiguous approval is sufficient.
- **F. Follow-up Task.** Due today plus `policy.close.followup_days`, Subject names the downstream item awaited, linked to the admin Contact and Opportunity. Only when E was posted or a downstream status is pending.

Then wait. `skip` is an answer.

### 7. Apply

Fresh read before each write. Readback with changed fields and record link. Rejections: quote the CRM message, give one corrected proposal. A verified Closed Won is never reopened or undone by this skill.

### 8. Verify downstream

Re-read the downstream status fields in [references/close-fields.md](references/close-fields.md). Report each item as `verified`, `pending`, `blocked` with the error text, or `not applicable`. Self-serve billing cancellation, invoice issued, and org linkage are verified only by a system field or an ops owner's reply in the handoff thread. Never infer them.

### 9. Close

Five lines or fewer: Closed Won date and source, proposals applied and skipped, each downstream item with its status, the owner of anything pending. Nothing sent by email.

### Refuse

Closed Lost (route to `pipeline-review`). Changing signed terms to fit the record. Reopening a verified close. Sending email. Any operations message without explicit authorization for the exact message and destination. Creating a free trial outside A0. Closing a product type without a configured flow. Resolving an org UUID by name. Closing more than one Opportunity per run.

## Outputs and readiness

Save the deliverable and exact proposals in `output/{run-id}/01_review.md`; show the relevant readout in the conversation. Declare every source receipt and proposed artifact in its `artifacts` list. A read-only run has no effects. Readiness requires the checks above and explicit source gaps; unsupported effects stay withheld. Record the actual conversation review in `review.json`, and applied, pending, failed, or skipped effects in `02_result.json` through the shared run lifecycle.

## Human check

Review the scope, evidence and exact payloads. Approval covers only the listed effects and revision. Fresh reads and independent provider readbacks are required for external effects.
