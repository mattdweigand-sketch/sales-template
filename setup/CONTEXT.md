# Configure the factory

Inputs: [questionnaire.md](questionnaire.md), _shared/policy.example.json and _shared/adapters.example.md.
Process: follow [installation.md](installation.md), collect only missing answers,
and write local configuration in the owning files. Existing setup is edited by diff.
Outputs: _shared/policy.json and _shared/adapters.md.
Human check: review configuration, connector access and one synthetic run before live effects.
Do not copy customer data, access tokens or prior-run artifacts into the public template.
Read [portability.md](portability.md) for what requires organization-specific implementation.
Read [source-port.md](source-port.md) and [source-manifest.json](source-manifest.json)
to inspect source coverage and deliberate adaptations.
