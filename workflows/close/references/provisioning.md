# Optional provisioning

Disabled by default. Configuration is not authorization to execute.
Before offering this effect, the organization must provide a reviewed contract:

1. Exact provider/tool, verified customer/account identity and eligibility criteria.
2. Request schema, allowed fields, required preconditions and all effects (including
   invitations, subscriptions, charges or messages).
3. Duplicate detection/idempotency behavior and how unknown success is reconciled.
4. Independent success/error/status reads, polling limits and escalation owner.
5. Any temporary record changes, captured preimages, and the distinct compensation
   or restoration procedure. A record restore cannot claim downstream reversal.

Display resolved payload and side effects under a separate proposal. Fresh-read
before execution, write once, verify independently and report unresolved outcomes.
After any terminal attempt, compare temporary fields with captured preimages.
Propose each necessary restore separately, preserving concurrent changes. If no
safe mapping, readback or recovery contract exists, keep this as a manual handoff.
