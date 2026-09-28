# Local validation

The portable rebuild was checked on macOS with Python 3.12.14.

- 174 synthetic tests passed. They cover source coverage and pagination, fiscal
  quarters, activity/next-step hygiene, mail evidence, forecast arithmetic, task
  dispositions, setup, run isolation, receipt integrity, pilot metrics and PDF
  failure handling.
- All seven pointer skills passed the skill frontmatter validator. Registry,
  pointer parity, procedure references, policy references, links and public
  packaging checks passed across 75 distributed files.
- Setup preserves existing private settings and blocks unconfigured workflows.
  Changed policy hashes invalidate configuration review. Write capabilities are
  checked separately. A supplied pilot export does not require CRM identity or
  fiscal configuration. Optional close integrations are disabled by default;
  enabling their effects requires explicit capabilities and contracts.
- Receipt checks cover byte preservation, duplicates, tampering, missing pairs,
  stale/future/naive timestamps, symlinked evidence and complete cursor chains.
  Pilot checks reject wrong account, window, units, unknown users and duplicate
  activity IDs. Quantities use exact decimals and round only for display.
- A synthetic pilot export ran through raw receipt capture, scope validation,
  calculation, HTML, installed macOS Chrome printing and PDF inspection. It used
  fictional workshop branding and hours: 33 active users from a 34-user roster,
  33 activity records and 569.25 hours. All three Letter pages were rendered and
  visually checked, including repeated table headers and heading placement.
  Rendering uses system fonts and no remote assets. Invalid or unfinished PDF
  candidates do not replace an existing report.
- A clean Git export independently passed the full test suite, public checks,
  initialization and all seven external run routes. Unconfigured doctor checks
  failed as intended. The ZIP includes the hidden skill pointers and excludes
  private settings, credentials, caches, customer data, runs and Git metadata.
- The distributed files were inspected for source branding, deployment IDs,
  custom API fields, private endpoints, product claims and company-specific
  pricing, billing and provisioning assumptions. Source-label and custom-field
  regression checks guard against reintroducing those dependencies.

These checks establish local mechanics with synthetic data. The configured CI
matrix (Linux/macOS, Python 3.10/3.12) has not run remotely. No live CRM, mail,
calendar, transcript, analytics, handoff or provisioning workflow was exercised.
No external message, business write, provisioning action or automation was created.
Actual provider mappings, permissions, source meaning and each exact external
effect still require deployment-specific verification and user review.
