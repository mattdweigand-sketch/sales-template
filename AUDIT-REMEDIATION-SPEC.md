---
type: implementation-spec
status: implemented
baseline_commit: 6820a68e9c255c1b15ab06ba746af8b82ae31b72
scope: sales-template
---
# Sales template audit remediation specification

This specification addresses every finding in the repository audit, including
the smaller errors, duplication, ICM walk-test failures, and judgment-placement
gaps. The approved implementation contract is retained below; section 15 records the
completed changes and verification. This document grants no external authority.

The implementation should stay small. Keep the five workflows, current folder
layout, generated pointers, Python standard library, and existing run lifecycle.
Prefer correcting an existing function or contract over introducing another
abstraction. Add only two focused calculation helpers: forecast arithmetic and
fixed task-triage decisions. Extend the existing run checker rather than build a
workflow engine.

This is a maintainer specification, not a runtime workflow reference. Do not add
it to ordinary workflow Load lists or approval snapshots.

## 1. Baseline and completion criteria

The audited snapshot has 66 tracked files, five workflows, and 78 passing tests.
The audit also inspected 14 ignored Python caches. Passing tests did not cover
the reproduced failures.

Implementation is complete when:

1. Every row in the traceability table below has its specified disposition and
   acceptance evidence.
2. Existing behavior remains intact except for the explicitly corrected rules.
3. Required checks run on actual input files before effects can be recorded as
   approved locally; a manually written ready flag cannot substitute for them.
4. Incomplete evidence remains visible. It never silently becomes zero, false,
   out of scope, a complete forecast, or permission to act.
5. Routing, source ownership, generated pointers, setup instructions, and tests
   agree with the final implementation.
6. Synthetic checks pass on Python 3.9 and 3.12, including the exported install.
7. A final independent review checks the evidence and the ICM walk, not just test
   results. Real connector behavior remains a deployment verification task.

### Complexity limits

- No new framework, database, dependency, background service, or connector.
- No generic rule language, JSON Schema interpreter, plugin dispatch system,
  nested stage hierarchy, or numerical 60/30/10 compliance target.
- No second route registry. Keep scripts/wrapper-contract.json as the route owner.
- No new approval journal, event-sourcing system, or automatic legacy migration.
- Keep request.md, 01_review.md, review.json, and 02_result.json as the run surfaces.
- Add one small inputs.json per run to bind the existing validators to source
  files and exact proposed effects. Do not add separate source, check, claim,
  role, effect, and execution manifests.
- Keep interpretation of buyer language, identity conflicts, stage evidence,
  and writing quality with the model and human reviewer.
- Retain short local reminders where deleting them would make navigation harder.
- Do not refactor unrelated code or add tests that merely mirror implementation.

## 2. Finding-to-change traceability

A-numbers match the numbered audit findings. S-numbers cover the smaller issues
in their original order. B and J rows make the architectural observations
explicit so they are not lost during implementation.

| ID | Finding | Required disposition | Acceptance | Implementation |
|---|---|---|---|---|
| A01 | Unknown stage silently excluded | Validate stage before scoping | C01 | Implemented; evidence below |
| A02 | Incomplete search accepted | Validate intervals, selection, narrowing | C02 | Implemented; evidence below |
| A03 | Truncated email drives decisions | Read complete relevant bodies; retain digest for navigation | C03 | Implemented; evidence below |
| A04 | Buyer deferral still enters Commit | Deferral/conflict check before bucket selection | C04 | Implemented; evidence below |
| A05 | Substantive reply classified as OOO | Verified metadata or reviewed interpretation; unknown stays unknown | C05 | Implemented; evidence below |
| A06 | Bounce attributed to copied recipients | Use identified failed-recipient evidence | C06 | Implemented; evidence below |
| A07 | Partial mail generates definitive counts | Reuse complete paired receipt validation | C07 | Implemented; evidence below |
| A08 | Task-gap-only deals suppressed | Explicit extended candidate union | C08 | Implemented; evidence below |
| A09 | Missing evidence causes stage regression | Require affirmative evidence and supported destination | C09 | Implemented; evidence below |
| A10 | Wrong Account on Contact create | Reuse shared identity reconciliation criteria | C10 | Implemented; evidence below |
| A11 | Two meanings of forecast buffer | Pure arithmetic helper and selected-path buffer | C11 | Implemented; evidence below |
| A12 | Ready flag bypasses required checks | Fixed checks in runs.py using inputs.json | C12 | Implemented; evidence below |
| A13 | Worktree bypasses publication check | Discover repository through Git | C13 | Implemented; evidence below |
| A14 | Wrapper generation follows ancestor symlinks | Preflight every destination before writes | C14 | Implemented; evidence below |
| A15 | Installation omits dependencies | Document and test intact clean export | C15 | Implemented; evidence below |
| A16 | Wrong event ordering and DST dates | Instant ordering and configured ZoneInfo | C16 | Implemented; evidence below |
| A17 | Wrong blank-value semantics | Trim text; distinguish supplied false/zero | C17 | Implemented; evidence below |
| S01 | Notes freshness uses report date | Use newest valid stored-entry date | C18 | Implemented; evidence below |
| S02 | Forecast header order conflicts | Template owns title, coverage, notes order | C18 | Implemented; evidence below |
| S03 | No-transcript interaction identity absent | Persist verified occurrence ID or explicit local ID | C19 | Implemented; evidence below |
| S04 | Null receipt row crashes | Validate shapes with contextual diagnostics | C20 | Implemented; evidence below |
| S05 | One bad activity date aborts review | Return affected-source errors and block dependent findings | C20 | Implemented; evidence below |
| S06 | Local-midnight claim uses UTC | Construct midnight in configured timezone | C16 | Implemented; evidence below |
| S07 | Repeated editorial word | Correct the duplicated word | C21 | Implemented; evidence below |
| B01 | Repeated Load/Skip block | Retain concise local routing; remove unnecessary repeated procedure | C21 | Retained; concise local routing |
| B02 | Repeated action policy | Shared rules own common boundaries; workflows link and state exceptions | C21 | Implemented; evidence below |
| B03 | Repeated report-format constraints | One template and a short exception list | C21 | Implemented; evidence below |
| B04 | Generated text duplication | Retain generated representations and parity checks | C22 | Retained; generated parity verified |
| B05 | Orphan/stale ignored caches | Targeted local cleanup only; no tracked-file deletion campaign | C23 | Cleaned locally |
| J01 | Required contract checks absent from state | Fix with A12; keep completion claims bounded | C12 | Implemented; evidence below |
| J02 | Context load not verified/bounded | Explicit per-step loads and comparable static measurement | C24 | Implemented; evidence below |
| J03 | Forecast arithmetic in prompt | Fix with A11 | C11 | Implemented; evidence below |
| J04 | Fixed triage choices/date math in prompt | Small pure triage helper | C25 | Implemented; evidence below |
| J05 | History preservation left to prose | Validate proposed NextSteps transformations in existing helper | C26 | Implemented; evidence below |
| J06 | Writer/configuration checks incomplete | Small consumer-specific validation and exact effect binding | C12, C27 | Implemented; evidence below |
| J07 | Preimage/readback/recovery depend on instructions | Validate declared payloads; preserve pending results and explicit sequences | C28 | Implemented; evidence below |

## 3. Canonical ownership and file scope

All paths are repository-relative. Existing owning files remain in place.

| Area | Existing owners to change | Small additions |
|---|---|---|
| Scope and receipts | scripts/coverage_check.py; _shared/adapter-contract.md | None |
| Mail evidence | scripts/mail_evidence.py; scripts/mail_contact_stats.py; scripts/mail_thread_digest.py | None |
| Dates, blanks, history checks | scripts/hygiene_check.py | Small pure history-validation function |
| Forecast math | Forecast procedure, policy, report reference | scripts/forecast_math.py |
| Fixed task decisions | Task-triage procedure and followup policy | scripts/triage_check.py |
| Run readiness | scripts/runs.py; workflows/run.md; existing run templates | _templates/run/inputs.json |
| Identity reconciliation | Existing task-triage CRM-corrections reference; interaction procedure | Reuse the existing reference, no second policy file |
| Packaging | scripts/check_repo.py; scripts/wrappers.py; setup documentation | None |
| Dependency freshness | scripts/wrapper-contract.json | Add actual new/transitive dependencies |
| Tests | Existing four test modules | Focused forecast and triage test modules |
| Routing and documentation | Existing CONTEXT files and generated surfaces | No new router or folder |

Keep reusable chosen values in policy.example.json and local policy.json.
Keep fixed calculations and validation in Python. Keep genuinely interpretive
steps in workflow prose. A comment explaining a code rule is documentation, not
an independently configurable policy.

## 4. Correct scope and receipt validation

### 4.1 Opportunity scope

Validate each open-snapshot record before selecting in-scope rows:

- The row must be an object with a stable nonempty ID, owner identity, explicit
  open state, and a string StageName.
- Normalize the existing key or key - label convention once.
- A stage in configured stage_order but outside in_scope_stages is a recognized
  exclusion. A missing, blank, non-string, or unmapped stage is unresolved scope.
- Preserve the original open count and identify every unresolved record.
  Unresolved scope makes coverage incomplete; never silently drop it.
- For otherwise in-scope rows, validate AccountId and the fields needed to
  establish the requested period. Preserve existing CloseDate uncertainty rules.
- Validate that in_scope_stages and warning-stage settings are consistent with
  stage_order. A malformed policy is an error, not an empty selection.

### 4.2 Receipt shape and completeness

Reuse load_queries in coverage_check.py as the common paired-receipt checker.
Mail evidence code may import it; do not duplicate the cursor algorithm.

Require explicit initial cursor and terminal next_cursor values, including null.
Validate one complete connected page chain per query, invariant selection,
consistent total_count, unique IDs within that query, and referenced raw evidence.
Booleans are not integer counts. Validate row objects and required fields before
calling string/dictionary methods. Include file, query, record, and field context
in failures. Never turn malformed data into an empty successful result.

Different complete searches may overlap. Identical messages across queries are
deduplicated after each query passes; conflicting copies are errors. A provider
without native totals may use the existing terminal-page-derived total only when
the raw evidence supports that derivation.

Keep recovered failures in the original evidence location. Check successful
replacement chains without treating unresolved failures as successes. Passing
these checks validates represented evidence, not provider authenticity or access
to records hidden by permissions.

### 4.3 Time intervals and allowed selection

Use inclusive starts and exclusive ends in policy.identity.timezone.
The required mail interval includes the current local reporting day through the
collection cutoff. For date-only native filters, a finite end must be at least
the next local date. Native open-ended queries use explicit end_date: null.
An absent end_date is unknown; never infer that it means infinity.

| Selection | Required beginning | Required ending | Allowed narrowing |
|---|---|---|---|
| external_inbox | At or before yesterday | Covers reporting day, or explicit open end | Exclude exactly the configured internal domains; no account, address, subject, or other narrowing |
| account_inbound, pipeline | At or before activity_days lookback | Covers reporting day, or explicit open end | Include every known external Contact domain; no extra subject/contact restriction that excludes that scope |
| account_inbound, forecast | At or before current fiscal-quarter start | Covers reporting day, or explicit open end | Same complete domain scope |
| account_calendar | Configured lookback; yesterday for daily mode | Covers configured lookahead, including its last local day | Only the account/contact selection declared by the workflow |
| booked_in_quarter | Exact quarter start | Exact next-quarter start | Owned won-state selection |

Require the declared calendar selection to equal account_calendar. Normalize
domain case before set comparisons. Reject extra narrowing fields in the
normalized descriptor; projection and page-size options are not narrowing.
Review the native provider_query against its declaration as the adapter contract
already requires. Do not claim code can detect undeclared provider-side filters.

## 5. Correct mail meaning, completeness, and full-body use

### 5.1 Classification

Replace authoritative regex classification with a small optional classification
object on a saved message:

~~~json
{
  "classification": {
    "kind": "substantive",
    "basis": "content_review",
    "evidence_refs": ["raw/message-1.json"]
  }
}
~~~

Kinds are substantive, ooo, bounce, calendar, and unknown. Basis is
provider_metadata or content_review. Evidence references must resolve to saved
source material included in the review. These fields are traceable assertions,
not proof that a human or provider certified them.

Use provider metadata only for the meaning it actually establishes. A generic
auto-replied header proves automation, not necessarily out-of-office status.
Subject prefixes and body phrases may flag a review candidate; they cannot
decide message kind by themselves. A missing/unresolved classification stays
unknown for decisions that depend on it.

Keep existing output fields where possible. If an unresolved message could
change the unanswered interval, unanswered_count is null with an explanation.
Do not report false or zero as a substitute for unknown. A later confirmed
substantive reply can make an older ambiguity irrelevant to the current interval.

### 5.2 Bounce recipients

Add an optional delivery_failures list only when source evidence identifies
recipients. Each entry contains recipients (an address list), evidence_refs,
and status (failed, delayed, or unknown). Different outcomes use separate entries.
Only an identified recipient with confirmed failed
status receives a confirmed bounce consequence. Missing status remains unknown.
Read provider delivery metadata or a reviewed delivery report.

Never treat all addresses in a body, quoted To/Cc lines, signatures, or original
mail as failed recipients. Missing recipient identity remains unresolved.
Do not translate a delivery delay into a permanent address failure.

### 5.3 Complete mail before decisive counts

Extend the existing mail-statistics command with explicit --calls and --since
arguments that bind it to the paired receipts used for its searches. Reuse the
current normalized receipt rows and their raw email-envelope references.
Validate that the message IDs/content being counted correspond to those receipts.
Do not pass an unrelated complete query to bless a different message file.
Bind supplied message files to the receipts' exact raw-file references as well
as their message IDs; this also binds an empty result to its actual query.
Reject an unmatched input file or a missing part of its selected query chain.

For engagement searches add one documented contact_history selection using the
requested addresses and both directions. Declare actual temporal/filter scope.
The descriptor contains addresses, direction: both, start_date, and end_date;
use explicit null dates for an unbounded request. No extra mailbox/subject
narrowing can stand in for the requested complete sent-and-received history.
An all-history unanswered/cold decision requires the requested complete history;
a limited window must be labeled as such and cannot establish never-replied/cold
status outside that window.

Old email envelopes remain usable for digests and inspection. Without adequate
receipt evidence they produce an incomplete result, not authoritative counts.
Do not manufacture pagination or classification evidence during migration.

### 5.4 Full bodies for business decisions

Change Forecast and Pipeline collection to use digests for navigation only.
Read the complete relevant buyer message before using it for timing, commitment,
blockers, order status, stage proposals, or CRM wording. Read additional messages
needed to support or qualify the claim. Preserve full-body sources in the
existing artifacts list.
For each assessed deal, fully inspect its newest substantive buyer message before
finalizing a bucket or evidence-based proposal. Reading an older optimistic
message does not satisfy this check when newer relevant evidence exists.

Missing or truncated bodies are source gaps. A preview cannot establish that
there are no blockers. Keep the existing full outbound/inbound read before
drafting. Change the digest footer to warn about both decisions and drafting.
Do not fetch or load every mailbox body merely to satisfy this requirement.

## 6. Correct workflow decisions with small contract edits

### 6.1 Forecast deferral

Make the owned forecast policy state:

> A verified buyer statement placing signature or decision after the current
> quarter excludes the deal from the current-quarter call unless later verified
> evidence explicitly supersedes that timing. Unresolved contradictory timing
> requires input and cannot enter Commit or Upside.

Apply this before the existing Commit/Upside order. A newer unrelated message
does not supersede the timing. A stale CRM CloseDate cannot override buyer
evidence. A date equal to next-quarter start is outside the current quarter.
Interpretation and resolution of conflicting statements remain reviewed work;
do not replace them with keyword detection.

### 6.2 Extended Task candidates

Define the selection once in pipeline-review.md:

    daily candidates = in-scope rows with hygiene triggers
    extended candidates = daily candidates UNION in-scope rows with task_gap

Keep task_gap separate from hygiene triggers. Gap-only rows belong in extended
Record proposals when their action, due date, links, and evidence support a
create. Unknown deadlines never produce a Task. Do not double-count an
opportunity with both a trigger and a gap. Update report wording so a reviewed
deal with no hygiene trigger can still have an extended Task proposal.

### 6.3 Stage regression

Replace missing-evidence regression with affirmative evidence that a necessary
condition no longer holds. A request to reassess permits investigation; it does
not replace that evidence or authorize a write. An explicit user instruction
for an exact stage change is a separate, clearly attributed basis for a proposal.
Identify a supported destination stage; do not just subtract one stage.
Missing historical support or recent silence alone becomes needs input.
Preserve the current stage while that issue is unresolved.

### 6.4 Contact and Lead reconciliation

Generalize the reusable identity section in the existing CRM-corrections
reference and link Interaction Sync to it. Keep triage-specific Task edits in
their current section. Update the reference router and review dependencies.

Each proposed Contact Account needs evidence connecting that person, employer,
email, and verified CRM Account. Co-attendance is insufficient.
Search Contacts and Leads where the provider has Leads. Distinguish a provider
without Leads from an unavailable Lead search.

- Existing matching Contact: reuse it or propose the supported correction.
- Converted Lead: fetch and verify its returned Contact link.
- Unconverted Lead: do not treat it as a Contact or invent AccountId linkage.
  Report the required manual reconciliation/conversion if a Contact is needed.
- Ambiguous matches or missing required duplicate checks: no Contact create.
- Created Contact: downstream linkage uses its verified returned ID in the
  existing separate proposal/approval sequence.

Do not add automatic Lead conversion, merging, or identity-resolution scoring.

### 6.5 Interaction identity without a recording

Persist one interaction identity in request.md when the interaction is resolved.
Use a verified transcript meeting ID with its provider namespace, otherwise a
verified calendar occurrence ID. Distinguish recurring event occurrences.
For user-notes-only interactions, generate a stable local ID once and label it
local; it is not a fabricated provider ID.

Reuse the ID on resume. Check existing call activities by marker and supporting
date/participants. Preserve recognition of legacy Interaction markers.
A later transcript must link to the existing interaction instead of creating a
second log. Calendar presence alone does not establish that the call occurred.

## 7. Move only fixed calculations into small helpers

### 7.1 Forecast arithmetic

Add scripts/forecast_math.py as a pure calculation module with a small CLI.
It consumes assessed deal rows; it does not interpret email, choose sales policy,
query providers, or write CRM. Model-assessed buckets and their citations remain
reviewable inputs.

Each input row supplies stable deal ID, population (booked/current/next quarter),
assessed bucket where applicable, amount or null, currency, and revenue basis.
Use Decimal; never binary floating-point money math. Validate duplicate IDs,
finite amounts, supported bucket/population combinations, and compatible amount
bases. Treat bool as invalid numeric input and zero as known zero. Unexplained
negative values require review instead of silently changing the call.

    booked_total = sum(known booked amounts)
    commit_total = sum(known current-quarter Commit amounts)
    call = booked_total + commit_total
    upside_total = sum(known current-quarter Upside amounts)
    gap = target - call
    remaining_gap = max(0, gap)
    all_upside_buffer = max(0, call + upside_total - target)

Sort current-quarter Upside by descending amount, then stable ID. Select the
shortest prefix covering remaining_gap; if the call already meets target, select
none. If the list is insufficient, retain all eligible rows and the unmet amount.

    path_total = call + sum(selected path amounts)
    path_buffer = max(0, path_total - target)
    uncovered_gap = max(0, target - path_total)

The report's “Call plus these” sentence uses path_total and path_buffer.
all_upside_buffer is optional and separately labeled; no extra report section
is required. Pull-ins never enter these current-quarter sums.

Unknown booked/Commit amounts produce a known subtotal plus unknown count, not
a complete call. Withhold dependent gap/path math. Unknown eligible Upside
amounts leave the path incomplete and cannot disappear from the report.
An absent target suppresses gap/path/buffer calculations. Apply display rounding
only after calculation using existing reporting precision.

Proposed CLI:

    python3 scripts/forecast_math.py INPUT_JSON --policy POLICY_JSON

The input contains rows and the target resolved for the run's quarter. The
readiness checker verifies that target against policy and reconciles the row IDs
against the coverage snapshot. This prevents a handpicked subset from producing
an apparently complete calculation. JSON output includes totals, selected IDs,
unknown counts, and errors; human formatting remains in the existing template.

Minimal input example:

~~~json
{
  "quarter_start": "2026-07-01",
  "quarter_end": "2026-10-01",
  "target": "100",
  "rows": [{
    "deal_id": "example-deal-1",
    "population": "current",
    "bucket": "commit",
    "amount": "80",
    "currency": "USD",
    "revenue_basis": "configured-example-basis",
    "source_refs": ["raw/opportunity-1.json"]
  }]
}
~~~

population is booked, current, or next; bucket is commit, upside, or excluded
for current rows and null for the other populations. Amounts and target are
decimal strings or null. The local adapter supplies the reviewed revenue-basis
label; this example is not a business default.

### 7.2 Fixed triage branches and dates

Add scripts/triage_check.py as a pure helper for fixed comparisons. Keep it
separate from mail statistics so that Task decisions do not become hidden mail
parsing behavior. Do not add a rule engine or another policy file.

Inputs are the selected Task/thread identity and established facts: existing
draft, evidence completeness, active/cold/unknown relationship, last sent/reply/
held-meeting timestamps, unanswered count, recipient status, cooldown, channel,
and interpreted internal-prep/moved-meeting flags. Keep source references with
these facts. Unknown values remain unknown.

Preserve the existing order:

| Order | Condition | Result |
|---|---|---|
| Precheck | Existing draft for the selected thread/recipient | Held existing-draft item, no duplicate |
| 1 | Confirmed newer substantive reply/held meeting, moved meeting, or internal prep | Manual-response group; human chooses Complete or a date |
| 2 | Established cold contact, complete required history, unanswered threshold met | Recycle decision; offer existing Push/Recycle choices |
| 3 | Hold window, future cooldown, unconfirmed recipient, LinkedIn-only, or necessary evidence unknown | Hold with explicit reason |
| 4 | Confirmed recipient, complete relevant bodies, no existing draft, earlier branches false | Draft recommendation and proposed date |

Do not accidentally move Hold before Recycle while refactoring the current policy.
Unknown relationship is not cold. Scheduled or elapsed-unverified events are not
held meetings. A missing CRM Contact alone is a correction, not automatically a
hold when recipient evidence is independently sufficient.
With complete history and no prior outbound, a verified substantive inbound
belongs in manual response. Unknown outbound history is different and cannot
support a follow-up draft. Outbound messages need no response classification
merely to contribute to a verified sent count.

Use local calendar days, not business-day arithmetic:

- hold_until = local last-sent date + configured hold days; hold while today is
  before hold_until.
- draft next date = today + active/cold configured next-date days.
- Push and new recycle cooldown = today + cooldown_days.
- Multiple timed holds use the latest known release date. Unknown recipient,
  channel, or evidence problems receive no invented expiry.

The helper does not draft text, choose manual actions, create records, or grant
approval. Grouping uses the Task's selected thread, not a contact's unrelated
newest thread. Share a draft candidate only when mailbox, thread, recipients,
subject, body, and attachments are the same reviewed proposal. Different asks
or recipients on the same thread require reconciliation, not automatic merging.
Each Task remains accounted for.

Proposed CLI:

    python3 scripts/triage_check.py INPUT_JSON --policy POLICY_JSON --as-of TIMESTAMP

Minimal input example:

~~~json
{
  "tasks": [{
    "task_id": "example-task-1",
    "mailbox": "seller@example.com",
    "thread_id": "example-thread-1",
    "existing_draft": false,
    "mail_complete": true,
    "relationship": "cold",
    "last_sent_at": "2026-09-20T12:00:00Z",
    "last_reply_at": null,
    "held_meeting_at": null,
    "meeting_moved": false,
    "internal_prep": false,
    "unanswered_count": 2,
    "recipient": "confirmed",
    "cooldown_until": null,
    "channel": "email",
    "bodies_complete": true,
    "source_refs": ["raw/task-1.json", "raw/thread-1.json"]
  }]
}
~~~

relationship is active, cold, or unknown; recipient is confirmed, unconfirmed,
or unknown; channel is email, linkedin_only, or unknown. Boolean facts may be
null when unknown. Null message timestamps mean confirmed absence only where
the relevant complete evidence supports absence; otherwise their condition is
unknown. Existing-draft detection holds a Task even when draft body inspection
is still required; sharing two new draft proposals requires the full comparison.

## 8. Fix existing hygiene functions

### 8.1 Time

Use ZoneInfo(policy.identity.timezone) for local dates. Convert --as-of as an
instant into that timezone; use its local date. If --today is also supplied,
compare it with that converted date. Without --as-of, --today means midnight in
the configured zone; without either, use the current instant in that zone.

Order known Event starts by UTC instant, with stable ID for equal timestamps.
Do not create a midnight timestamp for date-only events. If a date-only event
could be earlier on the same day, expose ordering uncertainty. Preserve the
existing distinction between elapsed and confirmed attendance.

### 8.2 Blankness and malformed values

Missing, null, empty string, whitespace-only text, and an empty required
collection are empty. False and zero are supplied values. Wrong field types are
validation errors. Preserve a nonzero/true-only business constraint only as an
explicit documented field-specific rule; do not encode it as generic blankness.
Check known logical types directly (for example, Amount is numeric, not boolean).
For custom fields, apply a type check only when the adapter supplies a declared
type; otherwise use generic absence checks and disclose the unverified type.
Do not create a universal custom-field schema system for this cleanup.

Bad dates and malformed activities return contextual diagnostics. Retain valid
record diagnostics, but suppress dependent stale/new-activity/recycle conclusions
when an unknown activity could change them. If a malformed record cannot be
linked to a known account, treat its impact as unresolved globally. Return a
nonzero CLI exit for incomplete/invalid input, not a traceback or silent omission.

### 8.3 History preservation

Add a small pure validate_next_steps_change function to hygiene_check.py.
It takes the exact normalized preimage, proposed full value, and declared
operation. Use the same adapter-normalized plain-text representation for both;
retain original provider bytes in receipts.

Supported operations are only those already described by policy:

- Prepend a new dated next step, retaining all existing dated entries.
- Replace only an undated legacy Next first line, retaining dated history below.
- Insert an explicitly proposed factual history entry after an unchanged
  current first entry.
- Leave the field unchanged when no NextSteps effect is proposed.

Preserve retained text, ordering, punctuation, and line boundaries. Do not
silently reformat legacy history. If conversion from provider markup is lossy,
withhold the normal preservation check and require an explicitly reviewed full
field conversion; do not pretend raw-byte parity was proved.

This validator checks construction, not whether a new action or history claim
is true. Unsupported destructive/history-edit operations remain outside these
workflows unless separately scoped. Existing Description prepend operations
likewise retain the exact prior suffix; use a simple comparison, not a second
history framework.

## 9. Strengthen readiness without adding a workflow engine

### 9.1 One small binding file

Add inputs.json to the copied starter. It identifies the local files consumed by
existing checks. Identity stays in request.md; do not duplicate run/workflow IDs.
The code owns a small fixed required-input/check table for the five workflows.
No dynamic shell commands, validator plugins, or configurable execution graphs.

Example shape for pipeline review:

~~~json
{
  "started_at": "2026-09-23T09:00:00-07:00",
  "mode": "extended",
  "sources": {
    "calls": "calls",
    "opportunities": "opportunities.json",
    "tasks": "tasks.json",
    "events": "events.json"
  },
  "unavailable_sources": [],
  "effects": []
}
~~~

Use ordinary explicit type/field checks in runs.py and the consuming helpers.
Fields depend on the selected workflow; reject misspellings/unsupported fields.
An unavailable source identifies its name and concrete reason. It permits an
explicitly incomplete report; it never satisfies the required check.

Every referenced path is inside the active run. Reject absolute paths, traversal,
symlinked leaves/ancestors, and references to other runs. Include inputs.json,
all consumed files, receipt inventories and referenced raw evidence in the
existing review snapshot. Keep the existing artifacts list for additional
deliverables. Do not require people to maintain two lists of the same inputs.
Adding/removing a receipt in a bound directory must invalidate the snapshot.

### 9.2 Fixed required checks

| Workflow | Bound inputs/checks |
|---|---|
| sales-call-prep | Nonblank sourced brief, selected call/source references, explicit gaps; validate mail completeness if mail statistics were used; no external effects allowed |
| interaction-sync | Persisted interaction identity, transcript or user-note source, account/contact reconciliation evidence, exact effect fields, history preservation for applicable changes |
| task-triage-speed-run | Selected Task census, matched evidence, complete mail inputs for dependent decisions, triage helper output recomputed from inputs, exact effects |
| pipeline-review | Open snapshot, Tasks/Events, paired receipts, daily/extended coverage checker, hygiene checks, exact effects/history checks |
| forecast-weekly | Paired forecast receipts, complete populations, source-linked assessed rows, recomputed arithmetic, exact effects/history checks |

Checks must consume actual input data. A saved passed boolean or text saying a
checker ran is not accepted as proof. Import existing functions directly.
Recompute checks for validate, record-review, and status; no caching framework.
Verify calculation/triage populations against the bound source census so omitted
records cannot pass merely because the supplied subset is internally consistent.

Reject an empty review and an unchanged starter with only its status switched.
Preserve semantic review as a human/model task; do not build a prose-quality
classifier or claim section headings prove a useful deliverable.

### 9.3 Reviewable partial work versus permission to act

Add one CLI command:

    python3 scripts/runs.py validate RUN_ID

It returns structured errors and these simple booleans:

- can_review: required local structure and an actual deliverable/gap report exist.
- report_complete: all required source/computation checks for that report pass.
- ready_for_effects: required checks and proposed effect structure pass.

Exit 0 means required checks pass; exit 1 means incomplete/invalid with errors.
status remains read-only and retains its existing state names. Add the booleans
and reasons to its output. review_current still means the recorded review matches
current bytes; it is insufficient for effects when ready_for_effects is false.

record-review always invokes validation. Review-only recording is allowed for a
well-formed, explicitly partial report with no approved effects. Any approved
effect requires the selected workflow's applicable checks to pass.

Keep the first implementation conservative: if it cannot establish that a failed
required check is irrelevant to an effect, withhold that effect. Continue useful
read-only findings. Resolving the source or explicitly narrowing and reviewing
the run is sufficient; do not add per-effect dependency graphs just to optimize
partial execution. Do not invent unaffected status from an unstructured error.

A partial read-only deliverable may reach completion_recorded with
report_complete: false clearly retained. It must never be described as a complete
forecast. Hashes and checks do not prove human authorization or provider success.

### 9.4 Exact effects with the same inputs file

When effects are proposed, inputs.json contains a small list with ID, operation,
destination, record identity, preimage, complete payload, and source references.
For a create there is no invented record ID. For an unsent draft include exact
To/Cc/Bcc, subject, body, attachments if any, and thread/reply identity.

The declared IDs must match the Effect headings in 01_review.md; approved IDs
remain a subset. The human review displays the exact proposal from these values.
The machine-readable entry owns the full payload; do not maintain an independently
edited second payload. Keep the current compact report where unchanged history
is omitted, backed by the full value and deterministic preservation check.

Validate the few operations the workflows already permit. Reject sends,
deletes/merges, unknown operations, missing record identities, and fields forbidden
by the selected workflow. For example, Call Prep has no external effects; Forecast cannot
change StageName or Amount. Keep these checks small and explicit.

NextSteps proposals invoke the preservation validator automatically based on the
changed field. The author cannot suppress it by omitting a check name.
Snapshot every full proposal so changed records, recipients, payloads, or evidence
invalidate the existing review. Existing exact approved local configuration
postimages remain supported; do not remove their recovery behavior.
An explicitly requested local configuration replacement remains a narrow
exception using the existing declared shared-input and expected_after rules,
including under a read-only sales workflow. It grants no external capability.

### 9.5 Apply and recovery stay in the existing lifecycle

Before each external effect: current review, actual authorization, passing
applicable checks, fresh provider read, exact preimage comparison, then write and
independent readback. Use the existing host adapters; no new executor.
The fields checked in a preimage include every field the proposal relies on,
not only the fields being changed. Absent and null are distinct.
Save these new preimage/provider/readback receipts outside the frozen collection
directories, for example under effect-evidence/. Reference them from
02_result.json and check them against the frozen proposal. They do not join the
already-approved collection snapshot or make it stale merely by being added.
Changing original collection evidence still invalidates that approval.

Use 02_result.json to record a pending attempt before calling the provider, then
update it with the provider result and readback references. Keep all approved IDs
accounted for; use pending with attempt_started_at: null for untouched rows,
and set that timestamp immediately before the provider call. Timestamped pending
means an uncertain attempt requiring reconciliation; untouched rows may begin
after the ordinary checks. Write this
small JSON file atomically to avoid partial records. Do not introduce a second
journal or claim atomic local writes make provider operations transactional.

On interruption or uncertain outcome, inspect existing provider evidence and
reconcile before retrying. Do not erase pending results when recording a revised
review. Preserve prior result/evidence files as declared run artifacts if a new
review replaces their current presentation.

Keep dependency handling explicit in the two procedures that need it:

- A Task date move justified by a new draft follows verified draft creation.
- A link to a newly created Contact/call Task uses the verified returned ID and
  the existing required separate exact proposal.
- A failed prerequisite withholds its dependent effect; unrelated approved rows
  may continue where their readiness is established.

These local checks constrain the declared workflow. They do not intercept every
host tool call or authenticate a reviewer, source, or provider.

## 10. Packaging, installation, and documentation

### 10.1 Git-aware public-file inventory

Use git rev-parse to identify a repository and its root. Use git ls-files for
ordinary checkouts, linked worktrees, and separate Git directories. Include
tracked ignored files so private-material checks can reject them.
Confirm the discovered root is the intended target; an exported subfolder inside
an unrelated repository must not scan that parent's inventory.
Use the existing export fallback only for a confirmed non-Git tree. Unexpected
Git failures in a known repository are errors, not a fallback signal.

### 10.2 Wrapper writes

Before any write, validate all planned destinations and their existing ancestors,
including route/workspace ancestors. Reject symlinks and paths outside the
canonical root. Preflight the full set so a late bad destination cannot leave
earlier generated files changed. Retain refusal to delete unknown wrappers.
Use atomic replacement per file and report any subsequent I/O failure honestly;
do not add a multi-file transaction framework.

### 10.3 Installation

Replace the incomplete host-specific copy list with an intact clean repository
export that retains hidden generated pointers, setup, examples, tests, and links.
Exclude Git internals, credentials, deployment files, customer outputs, and
caches. Prefer an ordinary export of the reviewed Git tree; no custom slim
packager or separate deployment variant.

Test the exact documented export in a temporary directory. Run its checks, tests,
and a synthetic run initialization. Provider authentication and host path support
remain explicitly unverified until that deployment is tested.

### 10.4 Report accuracy and cleanup

The forecast report reference owns the header order: title, actual coverage
result, then note freshness. The workflow links to that layout.
Use Notes as of the newest valid stored-entry date returned by the hygiene
checker, not report date and not an unsupported history-only interpretation.
With no valid dated entry, state that the note date is unknown.

Keep the pipeline report's actual template and one concise exception list.
Remove repeated restatements of its headings/preservation rules. Keep the
important distinctions: first entry versus full field, history change versus
no change, needs-input versus approvable proposal, and exact prior snapshots.

Keep shared boundaries in _shared/rules.md; workflows retain operation-specific
restrictions and short links. Keep local Load/Skip reminders and make policy
sections/references explicit for each step. Correct the repeated editorial word.
Do not change customer-facing formats solely to save prompt characters.

### 10.5 Context and caches

Measure comparable static reading bundles before/after: entry/router, selected
contract, necessary shared sections, selected example-policy keys, and conditional
references. Report character counts and the labeled characters/4 proxy; use a
real tokenizer only if already available. No new tokenizer dependency or score.

Aim for the ICM 2k-8k working range through selective reads. For larger evidence,
work per account/record or batch and retain cited files. Never truncate decisive
evidence to meet a size target. Explain any remaining oversized static bundle.

Remove only the identified stale/orphan cache files during authorized cleanup,
after confirming they remain ignored and reproducible. Retain ignore rules.
Do not commit cache deletions, scan unrelated caches, or delete tracked files on
the assumption that apparent disuse proves they are dead.

## 11. Acceptance tests

Tests use synthetic inputs and temporary directories. Prefer adding cases to
the existing modules; add focused modules for the two new helpers. Documentation
and interpretation changes use explicit fixture-based walk tests rather than
brittle assertions that a particular sentence exists.

| Test | Required cases and expected result |
|---|---|
| C01 | Missing/null/blank/numeric/unmapped stages produce incomplete scope with record IDs; recognized out-of-scope stages exclude normally; custom stages and key-label format work |
| C02 | Each revenue mode rejects empty/reversed/expired/missing-bound intervals and unsupported narrowing; explicit open end and adequate finite end pass; calendar requires account_calendar; domain case and legitimate supersets work |
| C03 | A qualification after character 300 affects the assessment; missing full body is a gap; unrelated supported findings remain visible; digest stays bounded |
| C04 | S4 with buyer next-quarter deferral is excluded; next-quarter boundary date is outside; genuine later supersession is considered; unresolved conflicting timing is needs-input |
| C05 | The substantive out-of-office sentence is unknown until reviewed, not OOO by regex; reviewed substantive resets unanswered count; relevant later unknown response makes it unavailable; older unknown before a confirmed reply does not spoil the later interval; subject/quoted text do not override content |
| C06 | Only identified recipient with failed status receives bounce consequence; unrelated To/Cc/signature addresses do not; missing status/recipient and delayed delivery remain unresolved rather than permanent bounce |
| C07 | Missing/cyclic/orphan/unreturned pages, changed selection, count mismatch, absent terminal marker, and conflicting copies fail; complete empty/multipage results pass; unrelated complete-empty query cannot bless a file; old envelope alone cannot yield decisive counts |
| C08 | Gap-only record appears only in extended Task candidates; existing matching Task removes gap; both trigger and gap do not duplicate the opportunity; unknown deadline prevents create |
| C09 | Old un-retrieved stage evidence or recent silence does not cause regression; a reassessment request alone supplies no contrary evidence; affirmative contrary evidence can support a destination; unknown destination remains needs-input |
| C10 | Consultant does not inherit customer Account; duplicate Contact prevents create; unconverted Lead is not treated as Contact; converted Lead link is verified; ambiguous matches/required search failure withhold create |
| C11 | Call 80, target 100, Upside 50+30 yields path 50, total 130, path buffer 30; all-Upside buffer 60 only if separately labeled; ties stable; target met/absent, insufficient upside, null/zero/non-finite amounts, duplicate IDs and currency/basis mismatch handled |
| C12 | Empty ready-marked forecast fails; missing inputs fail; authored pass flag cannot bypass recomputation; changed collection inventory/helper stales review; partial review allows zero effects with explicit gaps; disallowed effects fail; legacy draft/reviewed/completed/pending runs remain inspectable but unvalidated, and added bindings do not renew approval |
| C13 | Ordinary repo, real linked worktree, separate Git directory, and export tested; staged policy/adapters/output rejected in Git; ignored untracked local config stays allowed; Git errors do not silently pass |
| C14 | Symlinked skills/commands/workflow parent, command subdirectory, and leaf rejected; outside sentinel remains unchanged; no generated destination changes on preflight failure |
| C15 | Documented clean export passes local checks/tests and synthetic init; all routers resolve; private files and caches absent |
| C16 | 16:00-before-09:00 input selects 09:00 regardless of order; date-only ambiguity retained; LA autumn/spring and repeated-hour cases correct; --today means configured local midnight; inconsistent --today/--as-of rejected |
| C17 | Null/empty/whitespace fail required text; false is supplied for a checkbox but invalid for numeric Amount; zero is known; custom unknown types are not invented; explicit nonzero business rule is separate |
| C18 | Today's report shows last week's note date; no dates yields unknown; title/coverage/notes order agrees in procedure and reference |
| C19 | No-transcript resume reuses ID; same-day separate calls and recurring occurrences stay distinct; later transcript does not duplicate an existing call log; no fabricated provider ID |
| C20 | Null/scalar rows, bad IDs/AccountId, malformed dates, naive timestamps, boolean counts and malformed sender/attendee shapes produce contextual errors without traceback; valid unrelated diagnostics survive without hiding incomplete scope |
| C21 | Human diff review confirms editorial fix, one common action-policy owner, one report layout, preserved exceptions and useful local routing |
| C22 | Existing generation produces matching root/family maps and all ten pointers; new/transitive helper and reference dependencies invalidate affected approvals |
| C23 | Only identified ignored caches cleaned; tracked source unchanged by cleanup; no need to keep caches absent after normal Python execution |
| C24 | Comparable per-workflow static bundle measurement and cold walk; reduced unnecessary loading; no loss of full-evidence requirement or newly duplicated policy |
| C25 | Hold boundary before/on/after expiry; Recycle retains precedence over timed Hold; incomplete history and active contacts never recycle; existing draft holds; unverified meeting not active proof; no Contact alone not a hold; correct thread; conflicting draft payloads not merged; no-prior-outbound differs from unknown; missing bodies block draft; offsets remain calendar days |
| C26 | Valid prepend/legacy replacement/history insertion accepted; removed/reordered/rewritten dated history rejected; unchanged-current history insert preserves first entry; Description retains prior suffix; unknown lossy conversion is not certified |
| C27 | Invalid modes/timezones, inconsistent stages, malformed thresholds/precision, unsupported source settings, and invalid route bindings fail clearly; configured custom stages and reviewed deployment values remain supported |
| C28 | Changed preimage/recipient/payload invalidates eligibility; new effect-evidence files preserve approval while collection changes stale it; untouched versus timestamped pending distinguished across interruption; pending evidence survives rereview; draft failure blocks related Task move; verified IDs required; existing local-postimage recovery and wrong-postimage rejection preserved |

Preserve the existing tests for run isolation, stale approvals, explicit local
postimages, date ambiguity, attendance limits, wrapper parity, and source errors.
Add regressions for failures rather than replace them with weaker smoke tests.

## 12. Implementation order

1. Correct the small policy/procedure/report contradictions and add their fixture
   walkthroughs: A03/A04/A08/A09/A10, S01/S02/S03/S07.
2. Fix receipt validation, mail semantics/completeness, and hygiene edge cases.
   Update adapter examples and existing helper tests in the same change.
3. Add and wire the two pure calculation helpers. Define their data inputs once.
4. Add the small inputs binding, fixed readiness checks, and effect/history
   validation to the current run lifecycle. Test partial reviews and recovery.
5. Fix Git/worktree inventory, wrapper preflight, and the intact installation.
6. Update dependency declarations and regenerate wrappers with the existing tool.
7. Consolidate repeated wording, measure context, and perform targeted cache cleanup.
8. Run the acceptance matrix, full existing suite, clean-export verification, and
   an independent cold ICM walk. Report remaining limitations explicitly.

Steps may be parallelized by independent file ownership, but shared receipt/input
contracts must be agreed before dependent helper/run changes. Do not let agents
independently invent competing completeness or approval schemas.

## 13. Compatibility, review, and validation

Do not overwrite an existing local policy/adapters file with the example.
Document a small configuration diff for any new optional metadata or required
input binding. Update synthetic fixtures and invocation examples together.

Existing runs remain readable. A run without inputs.json can be inspected with
an explicit unvalidated explanation; it cannot gain new effect eligibility from
its old ready flag. To continue it, add real bindings/evidence, rerun checks, and
review changed proposals under the existing rules. Do not generate fake source
receipts, silently renew approval, replay pending effects, or add a migration
command for this small format change.

Legacy mail can still be inspected. Making it decision-ready requires actual
completeness evidence, not a synthetic terminal marker. Preserve provider/raw
field mappings and old interaction markers.

Run from the repository root after implementation:

    python3 scripts/wrappers.py --check
    python3 scripts/check_repo.py
    python3 -m unittest discover -s tests -v

Run the same documented checks in a clean export and use the existing CI Python
3.9/3.12 matrix. Run representative synthetic lifecycle examples for all five
workflows, including one incomplete report and one pending-effect recovery.
Do not require live credentials for repository tests.

The implementation review must report:

- Each A/S/B/J ID as fixed, retained by design, or unresolved with a concrete reason.
- Test outcomes and manual fixture evidence, including the original reproductions.
- ICM entry/routing, required inputs/outputs, human review, current-run isolation,
  ownership, reference integrity, and context-load results.
- Any remaining dependence on model interpretation or host execution.
- Actual file/module additions and why each was needed.

Retained by design is appropriate for useful generated pointers and concise
Load/Skip reminders, not for a reproducible correctness failure.

## 14. Explicitly excluded scope

Do not add live integrations, automatic sending, stage-change execution, Lead
conversion, predictive scoring, probabilistic forecasts, automatic business-policy
tuning, new schedules, or organization-wide configuration management.
Do not modify other repositories or external installed skills during this work.
Do not publish or change deployment settings as part of implementing this spec.

These exclusions do not leave an audit finding untreated: each finding maps to a
small code/contract fix, a concrete check, or an explicit decision to retain
useful existing structure. Additional infrastructure requires an actual problem
that the simpler implementation cannot solve.

## 15. Implementation and verification record — 2026-09-23

All 36 findings above have a disposition. The five-workflow layout, one route
registry, stdlib-only runtime and prepare/review/apply lifecycle remain intact.
No provider was queried or changed, no deployment configuration was overwritten,
and no repository commit or publication was performed.

The production additions are two calculation modules, forecast_math.py and
triage_check.py, and one copied inputs.json starter. Existing helpers own the
other checks. Three focused test modules were added: forecast and triage tests,
and a separate packaging module for isolated real-Git/worktree/export fixtures.
The last is a small organizational departure from the proposed test-file list;
it adds no runtime abstraction. This specification remains outside workflow
loads and approval snapshots.

### Acceptance evidence

Tests use synthetic data; interpretation cases below were walked against the
final procedures rather than encoded as keyword classifiers.

| Acceptance | Result and evidence |
|---|---|
| C01 | PASS — coverage tests reject missing, numeric and unmapped stages while preserving the open count and recognized exclusions. |
| C02 | PASS — coverage tests exercise intervals, explicit null ends, case-insensitive domains, CRM narrowing, wrong calendar selection/addresses and legitimate supersets. |
| C03 | PASS, procedure walk — a body whose first 300 characters are optimistic but whose later sentence defers signature must be read in full; the digest cannot establish timing. Missing/null bodies block dependent triage effects. |
| C04 | PASS, procedure walk — an S4 buyer statement “signature October 1” is outside a July–September quarter. Exclude before Commit/Upside; explicit later September timing can restore ordinary criteria, while conflicting unresolved statements remain needs-input. |
| C05 | PASS — mail tests cover a substantive “out of office” sentence, reviewed classifications, later unknown replies and older unknown messages superseded by a substantive reply. |
| C06 | PASS — only an explicitly identified failed recipient gets a bounce consequence; copied addresses, delayed delivery and unattributed failure remain distinct. |
| C07 | PASS — receipt/mail tests cover complete empty results, cursor failures, booleans as counts, conflicting copies, wrong raw files and legacy envelopes without decisive completeness. |
| C08 | PASS — hygiene tests produce task_gap for a live unmatched action; procedure walk includes it in extended candidates only, deduplicates it with triggered records and withholds a create for an unknown deadline. |
| C09 | PASS, procedure walk — silence or un-retrieved older evidence supplies no regression basis. Affirmative loss of a current-stage condition plus evidence for the destination supports a proposal; a reassessment request alone does not. |
| C10 | PASS, procedure walk — a consultant attending a customer's meeting keeps their independently established employer/Account. Contact duplicates, converted/unconverted Leads and unavailable searches follow the shared reconciliation owner; no guessed Account or conversion. |
| C11 | PASS — forecast tests cover the 80/100/50+30 example, shortest path, separate buffers, ties, zero/null amounts, absent target, insufficient Upside and incompatible bases. |
| C12 | PASS — run tests cover ready-only starters, missing bindings, changed source bytes/inventories/nested references, complete source-census reconciliation, partial read-only completion, restricted effects and stale review dependencies. |
| C13 | PASS — real ordinary/worktree/separate-Git fixtures reject tracked private files; ignored deployment files and unrelated-parent exports are handled correctly. |
| C14 | PASS — wrapper tests preserve outside sentinels and every earlier destination when any route/target ancestor is symlinked or an unknown wrapper exists. |
| C15 | PASS — an actual clean Git archive of the finished public files passed both interpreter suites and all five workflow initializations/status checks. |
| C16 | PASS — hygiene tests cover instant ordering, date-only uncertainty, local midnight, DST transitions and conflicting as-of/today values. |
| C17 | PASS — hygiene tests distinguish whitespace/null/empty values from supplied false/zero; known numeric types reject booleans and unknown custom types stay disclosed. |
| C18 | PASS — hygiene supplies the newest stored-entry date. Procedure walk: September 23 report + September 17 latest note renders that older date and “no notes written this week” for Monday week start; no date is unknown. Report owns title/coverage/notes order. |
| C19 | PASS — interaction run checks require a namespaced persisted identity. Procedure walk reuses a local/calendar ID after resume, distinguishes recurring occurrences and links a later transcript without adding a second call log. |
| C20 | PASS — malformed/null rows return contextual failures. Completed undated Tasks, reversed Events and contradictory completion fields make affected activity conclusions incomplete while preserving unaffected diagnostics. |
| C21 | PASS — selective Load/Skip routing is retained, the repeated editorial word removed, identity rules share one reference and the pipeline report retains one template plus exceptions. |
| C22 | PASS — regenerated task maps/pointers match the single registry; review bindings include newly consumed helper dependencies. |
| C23 | PASS — only the three previously identified ignored orphan/stale caches were removed after verification. Tracked files and unrelated caches were retained. |
| C24 | MEASURED — comparable base bundles are recorded below; additional source/adapter references are loaded per step, never all customer data or sibling workflows. |
| C25 | PASS — triage tests cover branch order, boundary dates, latest timed hold, unknown conditions and same-thread draft conflicts. Run tests recompute selected-thread facts, reject different payloads/recipients, and prevent a Contact with a substantive reply elsewhere being labeled cold. |
| C26 | PASS — history tests preserve exact retained text/order/boundaries and reject destructive or lossy changes. NextSteps invokes the validator automatically; Description retains the exact prior suffix. |
| C27 | PASS — run/helper tests reject invalid consumed stages, thresholds, sources, precision and known writer field types. Supported fields differ by workflow and create/update operation; arbitrary custom-field types are not invented. |
| C28 | PASS — pending attempts require reconciliation, previous results/evidence must be preserved, exact type-sensitive preimages/payloads/readbacks are compared, and added apply receipts do not stale frozen source evidence. Draft-before-date and verified-ID-before-link sequences remain explicit host procedures. |

The independent verifier reproduced additional integration failures before
acceptance. Corrections cover operation-specific field omissions, duplicate or
mismatched drafts, null bodies, cross-thread relationship facts, missing activity
timing, source-filter narrowing, consumer configuration, nested source hashing,
shared-input ancestor symlinks, helper dependencies and false/zero equality.
Each was rechecked after correction; no actionable production finding remained.

### Test and export results

- Python 3.9.6: **172 tests passed**.
- Python 3.12.13: **172 tests passed**.
- Independent verifier: both full suites passed sequentially, plus separate
  adversarial reproductions of the corrected boundaries.
- `wrappers.py --check`, `check_repo.py` and `git diff --check`: passed; five
  routes and 73 public files. Generated pointers remain synchronized.
- Clean export: copied the finished public working files into a temporary Git
  fixture, committed only there, used the documented `git archive ... HEAD`,
  extracted it and ran both complete suites. Hidden pointers, setup, examples
  and tests were present; Git metadata, private configuration, output and caches
  were absent. Each of the five initialized exported runs reported draft with
  ready_for_effects:false.
- Actual validate/status CLI calls also passed for complete synthetic Pipeline
  and Forecast runs. The tests exercise all five workflows, partial review,
  review invalidation and interrupted-effect recovery without live connectors.

Python 3.12 reports the standard-library warning about Python 3.14's future tar
extraction default in the synthetic packaging test. It is not a failing check;
the tested archive is generated locally by the fixture and Python 3.14 is outside
the configured test matrix.

### ICM walk and context measurement

| Walk check | Result | Evidence |
|---|---|---|
| Entry and routing | PASS | AGENTS.md → CONTEXT.md → selected family/workflow; five routes |
| Exact inputs, outputs and human checkpoint | PASS | workflows/run.md Start/Prepare sections; inputs.json; family contracts |
| Current-run isolation and status | PASS | Run contract Apply/Status; source path, snapshot, partial-review and recovery tests |
| Ownership and reference integrity | PASS | One scripts/wrapper-contract.json; generated parity and check_repo; factory policy versus ignored run products |
| Context load | MEASURED | Comparable table below; exclusions and remaining oversized steps explicitly reported |
| Live host behavior | NOT VERIFIED | No provider calls; local checks do not establish permissions, authenticity or authorization |

There is no new workflow engine or automated semantic decision layer.

Comparable base review bundles include the complete entry/root/family router,
selected workflow and shared rules; Start/Prepare/Status lifecycle sections;
and selected example-policy objects serialized with two-space JSON indentation.
The same selection was measured at the audited baseline and final tree. Policy
objects: Call Prep identity/call_prep/research/tooling/crm; Interaction
identity/crm/interaction/call_prep/email_voice/followup/pipeline; Triage
identity/crm/email_voice/followup/tooling; Pipeline
identity/pipeline/reporting/cadence/tooling/crm/forecast; Forecast
identity/forecast/reporting/cadence/tooling/pipeline. Whole selected objects make
this conservative relative to the procedure's narrower field-level reads.

| Workflow | Baseline characters | Final characters | Baseline chars/4 proxy | Final chars/4 proxy |
|---|---:|---:|---:|---:|
| Call Prep | 15,496 | 17,987 | 3,874 | 4,497 |
| Interaction | 20,929 | 24,423 | 5,232 | 6,106 |
| Triage | 19,254 | 23,208 | 4,814 | 5,802 |
| Pipeline | 20,772 | 23,514 | 5,193 | 5,878 |
| Forecast | 22,245 | 25,779 | 5,561 | 6,445 |

These are static character estimates, not tokenizer counts or measured model
usage. Required input/effect contracts increased the base bundles. The pipeline
report reference separately fell from 9,675 to 5,580 characters (4,095 removed)
by consolidating repeated rules. Adapter sections, conditional references and
customer evidence are excluded from the base table and add real context: loading
both collection/report references together can push a revenue step above the
2k–8k working range. The procedures therefore name per-step sections and defer
Exact effects/Apply until needed; work per record/batch for evidence. No decisive
body is truncated to meet a token target, and no 60/30/10 ratio is claimed.

Buyer-language interpretation, actual employment/identity, classification truth,
provider permissions/authenticity and real human authorization remain review and
adapter responsibilities. Local validation recomputes represented facts and
rejects malformed or incomplete inputs; it does not certify a live deployment.
