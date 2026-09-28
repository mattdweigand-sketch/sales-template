# Optional schedules

Policy cadence is a suggested schedule, not an active automation. Validate a manual
run first. When the user explicitly requests a schedule, use Codex's automation
tool. Default to a heartbeat attached to the current chat; use a standalone project
job only when the user asks for a separate task per run. Bind the correct project,
workflow, timezone and capability limitations. Record the absolute repository
directory and its `.venv/bin/python` interpreter in the scheduled prompt; run
commands from that root. Do not depend on an earlier shell's activation or PATH.
Local execution depends on the computer and app being available.

A scheduled prompt should read AGENTS.md and the selected workflow, initialize new
external run evidence, collect fresh data and post proposals in the chat. It must
withhold writes without exact approval. Never carry an earlier run's approval into
a new run. Report changed findings, completion, failures or required input; remain
quiet on unchanged, non-actionable state unless periodic updates were requested.

The forecast status helper prints title/body JSON for the chat. It does not invoke
a notification API or create schedules. Render its status honestly, including
incomplete coverage and process review needs. Use the actual chat link only when
available; do not fabricate one.
