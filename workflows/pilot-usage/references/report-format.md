# Pilot review and report

Prepare an external review JSON before generating the report:

```json
{
  "account_id": "example-account",
  "customer_name": "Example Customer",
  "prepared_by": "Example Seller",
  "pilot_start": "2026-09-01",
  "pilot_end": "2026-09-30",
  "data_through": "2026-09-20",
  "reviewed": false,
  "categories": {},
  "interpretation": ""
}
```

Categories optionally map actual activity IDs to reviewed labels. Interpretation
contains only source-supported observations and labeled hypotheses. The reviewed
flag records local content review; it does not establish user approval to share.

Present: customer/product, pilot and report dates, roster size, active users,
activity count, total quantity with unit, per-user activity/quantity/observed days,
category quantities, reviewed interpretation and evidence limits. Avoid claims of
completion, cost savings, available balance or business value without independent
evidence. The helper rounds only display quantities after summing exact decimals.

## Handoff companion

In `<run>/outputs/review.md` and chat, include the fields required by
rules#pilot_handoff alongside links to the report and preserved source receipts.
Use the account_id from the reviewed source scope; record any verified CRM mapping
separately. If no CRM linkage was checked, say `CRM linkage unverified` rather than
treating the usage identifier as a CRM record ID. Record metric grain and limitations
from the reviewed source, not a guessed conversion. This companion supports a later
explicitly supplied handoff without adding CRM prerequisites to export-only reports.
