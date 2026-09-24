# Pilot usage report

Plain text, one named pilot. Record links use `policy.crm.record_url`. Format
amounts with `policy.reporting.currency` and dates with its `date_format`.
Use the deployment's activity label, unit and permitted feature labels.

```
# Pilot usage · <date>

## <Customer> · <stage if applicable> · <formatted amount if applicable> · pilot ends <date> · <link>
Participants <roster count> · active <active> (<pct>%) · last 7 days active <count>
Weekly active: <week 1> <week 2> ... (omit for pilots under two weeks)
Usage: <quantity> <configured unit> across <activity count> <configured activity label>
Allocation: <quantity> <unit> (omit when not applicable; name an unavailable lookup)
Top participants: <display name or stable ID> <quantity> · ... (up to policy.pilot_usage.top_users)
Inactive participants (<n>): <names or IDs> (or none)
Feature mix: <configured label> <pct>% · ... (state denominator; omit if not configured)
Use cases (<sample size> recent activity descriptions):
1. <theme> (<n>). "<audience-permitted example, max 120 chars>"
2. ...
Buyer said: <dated source-backed objective, or not established>

<Customer> reported. Nothing written.
```

Missing dates or measurements remain explicit gaps. Zero roster participants
prints `Participants 0` and omits participant percentages. It does not establish
that provisioning failed. Percentages use whole numbers; quantities use configured
precision. A failed source prints `<section>: not available, <provider reason>`.
Do not claim activity establishes completed work, business value or ROI without
separate evidence. Never convert units, infer grants or fabricate feature labels.
