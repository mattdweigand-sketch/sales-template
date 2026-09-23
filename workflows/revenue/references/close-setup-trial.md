# Setup provisioning (proposal A0)

Use only when the close path requires an organization, both organization IDs are
absent, and the configured provisioner supports this setup flow. Existing self-serve
organizations are reused. A0 is not a standalone free trial workflow.

## Before proposing

1. Confirm `policy.close.setup_trial.enabled`, adapter capability, exact payload
   mapping, success fields and timeout. The example leaves this disabled. The
   source used a one-day setup trial and a CRM-triggered provisioning flow; those
   native fields, prices and flow names are not portable. Without a configured
   flow, prepare the operations handoff and hold the close.
2. Resolve the admin from an existing Contact Role or explicit user instruction.
   Exclude configured internal domains. Precheck membership by verified email.
   A returned organization must be reconciled: reuse the customer's existing org;
   report another org or ambiguous ownership. Distinguish not-found from tool
   errors. A generic 404 must not be assumed to mean no membership.
3. Snapshot every field in `restore_after` and every paid term the actual payload
   will overwrite. In the source these included subscription type, billing
   interval, start, deactivation and trial end dates. Add any deployment-specific
   overwritten terms. Later B proposals restore the signed value, or the exact
   pre-A0 value when the agreement is silent.

## Proposal

Show one full record payload, actual resolved dates, current and proposed values,
admin identity, any automatically sent invitation, and the restore plan. Obtain
explicit approval for those effects. Fresh-read the preimage before applying.
Declined or failed A0 holds A and produces a proposed operations handoff.

## Verification and recovery

Read back the configured trigger, sync time, error, subscription ID and account
organization ID within the configured bound (the source used one minute). A reset
trigger or sync timestamp proves an attempt, not success. Require the configured
successful status, expected organization/subscription IDs and no error.

Missing billing/deactivation payload fields: quote the provider error and prepare
one corrected proposal. Existing-member error: show the returned organization,
reconcile ownership and reuse it or ask for the correct admin. Unknown success:
read status before retrying. Do not repeat the same failed payload blindly.
Other failures stay blocked with the exact error and named handoff owner.

After successful setup, verify every approved term restoration. If restoration
fails, report the partial state and hold dependent completion claims. Never leave
a paid deal silently marked Trial. A verified Closed Won is not reopened.
