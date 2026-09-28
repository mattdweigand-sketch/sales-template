# Set up this sales workspace

Use this process when the user says setup or when required configuration is absent.
Read [the questionnaire](questionnaire.md) and [installation](installation.md).
Ask only for unanswered items needed by the selected workflow. Existing answers
stay owned by private configuration; inspect them before asking again.

1. Initialize local example files with `python scripts/setup.py init`.
2. Collect identity, business policy and required adapter mappings. Edit only the
   private files; show a concise diff when changing an existing deployment.
3. Inspect the actual available connector schema and read access. Save non-secret
   mapping/verification notes in `_shared/adapters.json`. Credentials stay with the
   connector/MCP credential manager. Never put tokens in Git or chat.
4. Review policy with the user, record its SHA from `setup.py policy-hash` in the
   adapter configuration, and set mode to configured only when review is complete.
5. Run doctor for the selected workflow. Rehearse with synthetic evidence, then do
   a bounded read-only live check before offering a first exact write proposal.

Outputs: ignored `_shared/policy.yaml` and `_shared/adapters.json`; a setup summary
with configured capabilities, missing dependencies and validation limits.
No connector installation, external write, provisioning, message or schedule is
implied by setup. Use [adapters](adapters.md) for provider contracts and
[automations](automations.md) only when a schedule is explicitly requested.
