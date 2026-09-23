# Portability and scope

This repository ports the seven downloaded Sales skills, all eleven referenced
documents, the shared helper code and its regression scenarios into the existing
ICM owners. The generated skill and command wrappers remain thin pointers. See
[source-port.md](source-port.md) for the source inventory and adaptations.

The port preserves evidence attribution, exact effect review, fresh reads,
provider readback, source-specific collection, report formats, human-reviewed
pilot narratives and downstream close verification. Local review files remain
scoped to a task-supplied run ID and do not replace provider business state.

Reusable source defaults are supplied as examples, including stage criteria and
forecast rules. Review them for the deployment. Identities, native schema mappings,
quotas, credentials, channel IDs, prices, schedules and branded assets are not
configured. Pilot and close remain disabled until their required adapters are
mapped. Setup provisioning has an additional explicit enabled flag and payload.

Six SQL templates preserve the original query methods against documented logical
views. The pilot helpers accept saved warehouse results or complete normalized
JSON, then assemble, compute, validate, render and print. They do not authenticate
to a warehouse. System fonts replace private brand assets; optional local fonts
can be hash checked. The PDF renderer makes no dependency downloads.

Coverage checking uses paired, normalized request/result receipts in an explicit
run directory for daily, Friday and forecast modes. Native requests and responses
stay alongside them. It verifies represented scope, success and pagination; it
cannot authenticate provider responses or reveal records hidden by permissions.

Validation covers local behavior with synthetic data. It does not prove live
credentials, mappings, customer-facing prose, or downstream provisioning. A
published repository is a complete reusable port, not a connected production
installation. To make a deployment operational, configure the selected adapters
and verify real reads and separately authorized effects in that environment.
