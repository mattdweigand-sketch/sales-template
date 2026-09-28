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
