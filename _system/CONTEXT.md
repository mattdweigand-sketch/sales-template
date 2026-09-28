# Maintain the template

This folder owns repository tooling, dependencies, tests and maintenance documents.

## Inputs

| Source | Load |
|---|---|
| User request and Git diff | Exact change scope and existing edits |
| [Contributor guide](docs/contributing.md) | Layout, commands and pointer generation |
| [Validation](docs/validation.md) | What has actually been tested and its limits |
| [Provenance](docs/provenance.md) | Origin and distribution boundaries when relevant |

## Process

1. Inspect the affected owner and its referrers before editing.
2. Make the authorized change; update dependencies, routes and docs together.
3. Follow the contributor guide to regenerate pointers and run relevant checks.

## Outputs

A reviewable Git diff and validation results. Maintenance reports stay outside the
public template unless they are reusable documentation. Keep customer data private.

## Human check

Review the diff, workflow impact and test limits. Publishing follows the user's
requested destinations and scope; a local check is not permission to publish.
