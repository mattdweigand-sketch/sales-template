# Brief formats

Plain text, numbered or bulleted, no tables. Facts carry a source in parentheses or a link. Hypotheses start with `Hypothesis:`.

## Single call

```
# Call brief: <Company> · <External attendee(s)>

**Meeting:** <title>, <day date>, <start to end TZ>, <duration>. (<calendar link>)
**Attendees:** <external names, titles, emails>; <internal names>.
**Call type:** <intro | discovery | demo | proposal | customer> because <one clause of evidence>.

## Bottom line
Two to four sentences. Where the deal stands, what this call must accomplish, the main risk.

## Prior context
- Bullets, newest first. Each ends with its source: (CRM Task <date>), (mail <date>), (transcript <date>).
- Include what the seller promised and what the buyer asked for.

## Who is on the call
- <Name>, <title>, <tenure>. One line on their remit. (<source>)
- Repeat per external attendee.

## What the business does
- Three to five bullets. Business lines, scale, current strategy signals, AI or data moves, incumbent tools. Each with a dated link.

## Where to open
- Two or three bullets. Facts first, then `Hypothesis:` lines.

## Discovery gaps
- One bullet per item in `policy.call_prep.expected_information[type]` not established, written as `<item>: not established`.

## Prior calls
Skip this section if none. Otherwise date, attendees, two to five short buyer quotes, commitments, open questions.
```

Target length: 300 to 450 words for an intro, up to 600 for a proposal or customer call.

## Multi-call window

```
# <Window> call prep

<N> external calls <on date | from date to date>. Times <TZ>. For a multi-day window, add a `### <Day, date>` heading before each day's calls. One sentence naming the calls that need the most care and why.

## <time> · <Company>
- **Who and business** — <attendee, title>. <One sentence on the business.> (<link>)
- **Prior context** — <what has happened, stage, amount, close date, last touch>. (<CRM link>)
- **Opening focus** — <one sentence>.
- **Risk** — <one sentence>.
- **Discovery gaps** — <comma-separated items not established>.

Repeat per call in time order.
```

Target length: 90 to 130 words per call. If a call needs the single format, say so and offer it.
