# Complete Sales source port

Baseline: the seven Sales skill packages and shared files downloaded from the
original project on 2026-09-23. [source-manifest.json](source-manifest.json) records
34 source files, their SHA-256 hashes and destination paths: seven skills, eleven
references, eleven helpers, three regression files, policy and the helper README.
Private originals remain outside this public repository. Hashes identify source
bytes; they do not assert byte equivalence or prove semantic completeness.

## Coverage map

| Original package | Restored behavior | Destination |
|---|---|---|
| sales-call-prep | Calendar/CRM/mail/transcript/adoption collection, ordered call classification, research limits, single and multi-call formats, source-labeled gaps | [procedure](../workflows/engagement/sales-call-prep.md), one reference |
| interaction-sync | Stable interaction identity, buyer/seller quote boundaries, duplicate-call check, all six effect groups, attachment review, open-task closeout, independent readbacks | [procedure](../workflows/engagement/interaction-sync.md) |
| task-triage-speed-run | Uncapped due queue, email statistics, first-match groups, section approvals, contextual reply drafts, recycle and CRM correction procedure | [procedure](../workflows/engagement/task-triage-speed-run.md), one reference |
| pipeline-review | Daily and Friday collection, source coverage, mechanical hygiene, exact current/recommended/evidence report, rollups, field history, stage/date/amount/loss/task proposals | [procedure](../workflows/revenue/pipeline-review.md), two references |
| forecast-weekly | Booked, commit/upside/excluded, every eligible next-quarter candidate, target math, ranked path, evidence notes, CRM and category proposals | [procedure](../workflows/revenue/forecast-weekly.md), one reference |
| pilot-usage | Six query templates, report and PDF modes, grants/task rounding, reviewed narrative input, deterministic calculation/validation, two-page rendering/printing | [procedure](../workflows/revenue/pilot-usage.md), three references, seven helpers |
| close | Signed-term preflight, five close paths, all six effect groups plus setup provisioning, field source classes, restore plan, downstream statuses and handoff | [procedure](../workflows/revenue/close.md), three references |
| shared code | Mail contact stats/digest, current-run coverage, next-step/activity checks, source regression scenarios | [tooling](../scripts/CONTEXT.md), [tests](../tests/CONTEXT.md) |
| shared policy | Follow-up timing, call gaps, stage and forecast rules, pilot configuration and close terms | [example policy](../_shared/policy.example.json), [adapter contract](../_shared/adapter-contract.md) |

## Deliberate adaptations and source fixes

- Canonical procedures and references stay under their existing ICM family.
  Skills remain generated pointers. No duplicated full instructions were added
  to wrappers. The repository must travel with those pointers.
- Source YAML becomes JSON. Organization identities, connector IDs, live CRM and
  channel IDs, commercial pricing, quotas, warehouse identifiers, private guide
  links, production schedules and brand font URLs are excluded. Logical fields,
  views and operations replace vendor assumptions; their mappings are local.
- All helper inputs are explicit run files. Coverage now verifies paired success,
  complete cursor chains and counts in all three modes; the source's Friday and
  forecast paths had counted request presence. Normalized receipts still require
  retained raw sources and a scope review. A successful empty scope is supported.
- The dated next-step parser accepts deployment author labels and configured
  stage order. It preserves legacy reads, distinguishes written dates from due
  dates, and does not claim attendance from elapsed calendar events. Forecast's
  stale legacy write example was corrected to the current dated-sentence format.
- Mail counts compare timestamp instants, deduplicate messages and distinguish
  bounce, calendar, OOO and substantive replies. The digest now strips common
  quoted-thread formats and signed URL parameters. Missing result data is an error.
- Pilot assembly retains non-voided effective grants, per-task half-up rounding,
  unique task grain and exact reconciliation. It accepts normalized JSON or an
  explicit warehouse-call directory. Internal-domain rows are excluded. False-like
  strings cannot authorize narratives. The display describes tasks started;
  task rows alone do not establish completion. Fonts default to system fonts;
  local optional assets are verified. Failed printing retains the prior output.
- Setup provisioning is disabled until its payload and side effects are mapped.
  Precheck, paid-term snapshot/restore, failure hold and downstream readback remain.
  No organization-specific trial trigger, private price book or channel is assumed.
- New review dependencies include relevant references and helper code. Editing
  one invalidates the affected approval instead of reusing a stale revision.

## ICM walk

| Request | Entry and owner | Conditional detail | Output and review |
|---|---|---|---|
| Prep a named call | AGENTS → CONTEXT → engagement → sales-call-prep | Brief formats; relevant adapters | One run brief; no external effects |
| Review Friday pipeline | AGENTS → CONTEXT → revenue → pipeline-review | Collection, report format, hygiene/coverage helpers | Exact proposed changes with evidence and separate financial/stage approvals |
| Create one pilot PDF | AGENTS → CONTEXT → revenue → pilot-usage | Queries → PDF reference → pilot helper contract | Reviewed narratives, reconciled metrics, two-page PDF in private run |
| Close a signed deal | AGENTS → CONTEXT → revenue → close | Fields → selected path → setup only if applicable | Exact record/message effects; verified or pending downstream items |

The walk reaches all required resources through the selected owner without
loading another family's procedures. Factory rules remain separate from customer
outputs. A forecast run explicitly shares pipeline's collection reference only.

## Validation boundary

The regression suite covers review isolation/freshness, helper behavior, negative
coverage cases, date/time boundaries and pilot reconciliation. An optional real
Chromium integration test exercises assemble → compute → validate → render → print
and checks two Letter pages, metadata/content and failed-output preservation.
Visual inspection is required when the PDF template changes.

No tests call CRM, mail, warehouse, billing or operations connectors. Publishing
this port does not activate the original project's schedules or a live sales
deployment. Those require the local configuration described in
[installation.md](installation.md).
