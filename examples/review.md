---
type: synthetic-example
status: ready
---
# Example review

This is fabricated demonstration data, not a live run or approval.

## Scope and source coverage
One fictional account, Example Account. No external service was queried.

## Findings or deliverable
A fictional buyer asked for an example CSV export. The agreed evaluation date is not established.

## Effect A1
Display of the exact inputs.json draft payload (synthetic illustration only):

```json
{"to":["buyer@example.org"],"cc":[],"bcc":[],"subject":"Example CSV export","body":"Hi Alex, here is the fictional CSV example we discussed. Which fields should the next example include?","attachments":[],"thread_id":null,"reply_to_message_id":null}
```

An actual run also binds destination, source evidence and a fresh no-existing-draft
preimage as described in [the run contract](../workflows/run.md).

## Checks and unresolved work
This illustrates exact payload review. There is no actual recipient, provider
result, authorization or claim approval. A test must use an isolated run.
