#!/usr/bin/env python3
"""Build the forecast-weekly notification from verified coverage and the workflow status.

Usage: python3 forecast_notify.py --since <ISO datetime with offset, run start>
                                  --thread-url <URL of this run thread>
                                  [--summary "<one line: booked, call, gap, candidates>"]
                                  [--policy PATH] [--schedule "<cadence text>"]
                                  [--process-status ready|incomplete|review-needed]

Run with an explicit --calls directory. Runs coverage_check.py --scope forecast --since <since>
itself in JSON mode and checks its exit code, ready flag, and completion status. Prints one JSON status object for the Codex chat:
title "Weekly forecast ready" only when coverage is complete and the caller reports ready, otherwise
"Weekly forecast incomplete" with the coverage lines in the body. The body
carries the summary (when given), the coverage line, and the actual thread URL when available.
Exit 0 when the payload was built; exit 2 when coverage_check could not run.
Render the title and body in chat. This helper never sends or schedules a notification.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

COVERAGE = Path(__file__).resolve().parents[3] / "_shared" / "scripts" / "coverage_check.py"
READY, INCOMPLETE = "Weekly forecast ready", "Weekly forecast incomplete"


def run_coverage(since: str, policy: str | None, calls: str) -> tuple[int, str]:
    cmd = [sys.executable, str(COVERAGE), "--scope", "forecast", "--since", since, "--json", "--calls", calls]
    if policy:
        cmd += ["--policy", policy]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def build_payload(code: int, coverage: str, summary: str, thread_url: str, schedule: str | None, process_status: str = "ready") -> dict:
    try:
        result = json.loads(coverage)
    except ValueError:
        result = None
    ready = code == 0 and isinstance(result, dict) and result.get("ready") is True and result.get("process_status") == "complete" and process_status == "ready"
    lines = result.get("lines", []) if isinstance(result, dict) else [l for l in coverage.splitlines() if l.strip()]
    if process_status != "ready":
        lines.append("Workflow status: " + process_status)
    code = 0 if ready else 1
    parts = []
    if summary:
        parts.append(summary.strip())
    if code == 0:
        parts.extend(lines or ["Coverage ready."])
    else:
        parts.append("Forecast incomplete. " + " ".join(lines) if lines else "Forecast incomplete: coverage check returned no output.")
    if thread_url:
        parts.append(thread_url)
    payload = {"title": READY if code == 0 else INCOMPLETE, "body": " ".join(parts), "delivery": "chat"}
    if schedule:
        payload["schedule_description"] = schedule
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Forecast notification payload gated on coverage_check.")
    parser.add_argument("--calls", required=True)
    parser.add_argument("--since", required=True)
    parser.add_argument("--thread-url", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--policy")
    parser.add_argument("--schedule")
    parser.add_argument("--process-status", choices=["ready", "incomplete", "review-needed"], default="ready")
    args = parser.parse_args(argv)
    code, coverage = run_coverage(args.since, args.policy, args.calls)
    if code not in (0, 1):
        print(f"coverage_check did not run (exit {code}): {coverage}", file=sys.stderr)
        return 2
    print(json.dumps(build_payload(code, coverage, args.summary, args.thread_url, args.schedule, args.process_status)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
