# Forecast report

Forecast layout. Plain text. Dollar figures with commas, no cents unless the record has them. Record links use `policy.crm.record_url`.

```
# <Q3 2026> forecast · <M/D/YY>
<Coverage line from coverage_check>
Notes as of <M/D/YY>[. no notes written this week]

Booked $<booked> (<n> deals)
Calling
- <Account> $<amount>. <evidence clause: stage, buyer-named date, last touch>.
Forecast call $<call>
Gap to $<target> $<gap>

## Path to $<target>
1. <Account> | $<amount>. <Next line action>. Buyer date: <M/D only if the buyer wrote it, else none stated, "<buyer's words>">.
2. ...
<Call plus these reaches $<sum>, a $<buffer> buffer.> | <Upside does not cover the gap by $<n>.>

## Pull-in scope (<n>)
Every next-quarter S2+ deal with an Amount, one line each. No deal is omitted.
- <Account> · $<amount> · close <M/D> · CANDIDATE · <proposal or order form out, buyer confirmed reviewing on M/D | buyer named M/D> (<source>) · <Next line action>
- <Account> · $<amount> · close <M/D> · not · <failed condition> (<source>)

## Not in the call (<n>)
- <Account> · <stage> · $<amount or "not set"> · close <M/D> · <failed condition> (<source>)

## <Q4 2026> preview
<n> deals, $<sum>. Top: <Account> $<amount>, <Account> $<amount>, <Account> $<amount>. Target <set|not set>.

## Asks
- <who>: <what, for which deal, by when>
(or `None.`)

## CRM gaps (<n>)
A. <Account> CloseDate <old> → <new>. Evidence: <source, date>.
B. <Account> NextSteps current first entry → exact proposed dated sentence per policy.pipeline.note_next_line. Include a separate factual history entry only when proposed and supported. Preserve existing dated entries. Evidence: <source, date>.
C. <Contact> Email <old> → <new>. Evidence: replies from <new> on <M/D>.

## ForecastCategory sync (<n>)
D. <Account> <current> → <proposed>
...
Reply with letters to apply, or `skip`.
```

When the target is null, replace the Gap line with `Target not set.` and omit the Path section.
