# Forecast report

Forecast layout. Plain text. Amounts use policy.reporting.currency and amount_decimal_places; dates use policy.reporting.date_format. Never combine currencies without reviewed conversion evidence. Record links use `policy.crm.record_url`.

```
# <quarter> forecast · <report date>
<Coverage line from coverage_check>
Notes as of <newest valid stored-entry date | unknown: no valid dated entries>[. no notes written this week]

Booked <formatted booked> (<n> deals)
Calling
- <Account> <formatted amount>. <evidence clause: stage, buyer-named date, last touch>.
Forecast call <formatted call>
Gap to <formatted target> <formatted gap>

## Path to <formatted target>
1. <Account> | <formatted amount>. <Next line action>. Buyer date: <date only if the buyer wrote it, else none stated, "<buyer's words>">.
2. ...
<Call plus these reaches <formatted path_total>, a <formatted path_buffer> buffer.> | <Upside does not cover the gap by <formatted uncovered_gap>.>

## Pull-in scope (<n>)
Every next-quarter in-scope deal with an Amount, one line each. No deal is omitted.
- <Account> · <formatted amount> · close <date> · CANDIDATE · <proposal or order form out, buyer confirmed reviewing on <date> | buyer named <date>> (<source>) · <Next line action>
- <Account> · <formatted amount> · close <date> · not · <failed condition> (<source>)

## Not in the call (<n>)
- <Account> · <stage> · <formatted amount or "not set"> · close <date> · <failed condition> (<source>)

## <next quarter> preview
<n> deals, <formatted sum>. Top: <Account> <formatted amount>, <Account> <formatted amount>, <Account> <formatted amount>. Target <set|not set>.

## Asks
- <who>: <what, for which deal, by when>
(or `None.`)

## CRM gaps (<n>)
A. <Account> CloseDate <old> → <new>. Evidence: <source, date>.
B. <Account> NextSteps current first entry → exact proposed dated sentence per policy.pipeline.note_next_line. Include a separate factual history entry only when proposed and supported. Preserve existing dated entries. Evidence: <source, date>.
C. <Contact> Email <old> → <new>. Evidence: replies from <new> on <date>.

## ForecastCategory sync (<n>)
D. <Account> <current> → <proposed>
...
Reply with letters to apply, or `skip`.
```

When the target is null, replace the Gap line with `Target not set.` and omit the Path section.
Unknown booked/Commit amounts require a labeled known subtotal and unknown count;
omit gap/path claims that depend on a complete call. Unknown Upside means an
incomplete path. Never display unknown as zero. Use the helper's selected-path
buffer; any optional all-Upside buffer must be separately labeled. When the call
already meets target, the selected path is empty and no additional deal is required.
