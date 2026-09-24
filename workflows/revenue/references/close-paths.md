# Close paths

One path per run. The selecting fact comes from the record or the agreement, never from the deal name. Values referenced here live in `policy.close`.

Use the configured sales operations playbook for field mappings, pricing and provisioner behavior.

## 1. Standard annual

Selects when `DealType` is Annual Contract, the Account has no self-serve org, and one org is in scope. Terms per `terms_default`, `price_books.annual`. Skip proposal A when an existing signed-contract integration has already set StageName to Closed Won; verify its signature source and date. A missing org UUID means the org is absent or unlinked. When the configured no_org_rule requires it, hold the close until an existing org is verified or [setup provisioning](close-setup-trial.md) succeeds. Handoff only when A0 is declined or fails.

## 2. Self-serve to white-glove

Selects when the Account or admin tool shows an existing self-serve org with a self-serve billing subscription. Rules: reuse the existing org UUID, never create a second org. Handoff required: the ops post carries the UUID, the self-serve billing customer id when known, and asks for activation and self-serve billing cancellation without an access gap or double billing. Cancellation is `pending` until an ops owner confirms.

## 3. Multiple orgs

Selects when the agreement or the buyer names more than one org. Rule per `one_account_one_org`: each org has its own Account and Opportunity, child Accounts under one parent via `ParentId`. This run closes one Opportunity; list the sibling Opportunities and their state. Handoff required to link each UUID.

## 4. Paid pilot

Selects when `DealType` is Paid Trial. Rules per `paid_pilot`: `price_books.pilot`, the signed price and configured discount rule, `ContractTerm` = pilot length in months, `SubscriptionType` Paid. When the configured price book annualizes Amount, report the actual pilot charge beside it: seats x monthly unit price x months, with any separately signed credits or charges shown explicitly. An annual-term record with a heavy discount is a mismatch, not a pilot.

## 5. Renewal or expansion

Selects when the Account already has a Closed Won Opportunity with an active subscription and `Type` is Renewal or Existing Business. Same as standard; additionally confirm the new `SubscriptionStartDate` follows the prior `SubscriptionCancelDate` and that the org UUID on the Account is unchanged.

## Not a path

Standalone free trials (A0 runs only inside a close). Any product type without a configured close flow: collect the missing requirements and hold writes. Closed Lost: `pipeline-review`.

## Handoff template (proposal E)

Use the configured operations channel format, mentions from `ops_owners`, and supported record links. Facts only from the record and agreement. One ask per line.

```
<@owner1> <@owner2> <Account> close status: <verified Closed Won date or blocked before close>, <path name>. Signature confirmed by <evidence>.
<Opportunity link> shows $<Amount>, <term> months, <billing interval> billing, <seats by tier>, <credits> credits. Contract dates <start> to <end>.
Org: <UUID or "none on the Account">. <self-serve billing customer id line, self-serve path only>
Please <ask 1>.
Please <ask 2>.
CRM currently shows billing <status> and admin subscription <id or blank>.
```
