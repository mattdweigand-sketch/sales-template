---
cadence: <daily, weekly or one-off>
reads: <exact policy blocks, adapter capabilities and reference paths>
writes: <exact approved effects, or local artifacts only>
next: <state owner or explicitly supplied handoff, or none>
---

# <Workflow name>

Starter only, not a runnable workflow. Replace this paragraph with the workflow's
purpose. Keep the finished contract at most 80 lines and each reference at most 200.

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Policy | <private policy path> | <blocks actually used> | <configured values> |
| Providers | <private adapter path> | <selected capabilities and mappings> | <required reads/effects> |
| Shared rules | <rules path> | <exact anchors> | <relevant constraints> |
| Reference | <real reference path> | <exact heading and branch/step> | <what it defines> |
| Per-run evidence | <external run paths> | <selected scope> | <what it establishes> |

## Process

1. Check setup and initialize the external run per the shared run-start rule.
2. Collect the selected inputs per <reference and heading>.
3. Prepare the reviewable result per <reference and heading>, running Audit first.
4. For external effects, wait for the applicable exact approval, then fresh-read,
   apply and independently verify per the shared write protocol. Omit for read-only work.
5. Report actual results, gaps and unresolved outcomes in the external run and chat.

## Checkpoints

Delete this section for work that runs straight through. Describe existing review
boundaries; adding this table does not add an extra approval turn.

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 3 | <complete result or exact proposed effect> | <specific approval or correction> |

## Audit

| Check | Pass Condition |
|---|---|
| <check>, before step 3 output | <observable pass condition and existing helper if relevant> |
| <check>, before step 4 effect | <approval, fresh-read and independent verification requirements> |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Review | <external run review path> and chat | <Markdown layout with sources and gaps> |
| Evidence | <external raw/receipt paths> | <original bytes and normalized records> |
| Approved effects | <configured destination> | <exact payload and independent readback> |
