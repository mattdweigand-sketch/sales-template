# Pilot usage report

Plain text. One block for the named pilot. Record links use `policy.crm.record_url`.

```
# Pilot usage · <M/D/YY>

## <Account> · <stage> · $<amount> · trial ends <M/D> (<d> days) · <link>
Seats <provisioned> · active <active> (<pct>%) · L7 active <l7>
Weekly active: <wk1> <wk2> <wk3> ...          (omit when the pilot is under two weeks old)
Top users: <email> <n> · <email> <n> · ... (up to `policy.pilot_usage.top_users`)
Idle seats (<n>): <email>, <email>, ...      (or `none`)
Feature mix: Task product <pct>% · Search <pct>% · Chat <pct>% · Other <pct>%. Models: <model> <n>, <model> <n>.
Use cases (<sample size> recent queries):
1. <theme> (<n>). "<example, max 120 chars>"
2. ...
Buyer said: <one line from NextSteps or notes, with date>

<Account> reported. Nothing written.
```

Rules. No `TrialEndDate` prints `trial end not set`. A pilot with zero provisioned seats prints `Seats 0 · not provisioned` and omits the other lines through Use cases. Percentages rounded to whole numbers. Emails as stored. An erroring query prints `<section>: not available, <analytics provider message>` in place of that section only.
