#!/usr/bin/env python3
"""Generate thin skill and command pointers from one routing registry."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def safe_path(root, relative):
    """Validate every existing component before reading or generating a surface."""
    if not isinstance(relative, (str, Path)) or not str(relative):
        raise ValueError("path must be nonempty")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("path must stay inside repository: " + str(relative))
    root = root.resolve()
    dest = root / rel
    for part in [rel, *rel.parents]:
        candidate = root / part
        if candidate.is_symlink():
            raise ValueError("symlinked path: " + str(part))
        if part != rel and candidate.exists() and not candidate.is_dir():
            raise ValueError("path ancestor is not a directory: " + str(part))
    try:
        dest.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes repository: " + str(relative)) from exc
    return dest


def load_routes(root=ROOT):
    doc = json.loads(safe_path(root, "scripts/wrapper-contract.json").read_text())
    if not isinstance(doc, dict) or doc.get("version") != 1 or not isinstance(doc.get("commands"), dict):
        raise ValueError("invalid wrapper contract")
    for name, row in doc["commands"].items():
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name):
            raise ValueError("invalid command name: " + name)
        if not isinstance(row, dict) or set(row) != {"description", "workspace", "workflow", "review_inputs"}:
            raise ValueError("invalid route fields: " + name)
        if not isinstance(row["description"], str) or not row["description"].strip():
            raise ValueError("missing description: " + name)
        for key in ("workspace", "workflow"):
            if not isinstance(row[key], str) or not row[key]:
                raise ValueError("missing route path: " + name)
            target = Path(row[key])
            if target.is_absolute() or ".." in target.parts or not str(target).startswith("workflows/"):
                raise ValueError("route must stay under workflows/: " + str(target))
            if not safe_path(root, target).is_file():
                raise ValueError("missing or symlinked route: " + str(target))
        if not isinstance(row["review_inputs"], list) or any(not isinstance(p, str) for p in row["review_inputs"]):
            raise ValueError("review_inputs must be a list of dependency paths")
        for ref in row["review_inputs"]:
            target = Path(ref)
            if target.is_absolute() or ".." in target.parts or not target.parts or target.parts[0] not in ("workflows", "scripts", "_shared"):
                raise ValueError("invalid workflow review dependency: " + ref)
            if not safe_path(root, target).is_file():
                raise ValueError("missing or symlinked review dependency: " + ref)
    return doc["commands"]


def expected(root=ROOT):
    files = {}
    routes = load_routes(root)
    table = "\n".join(f"| `{name}` | [{Path(row['workspace']).parent.name}]({row['workspace']}) | {row['description']} |" for name, row in routes.items())
    files[Path("CONTEXT.md")] = (
        "# Task router\n\nGenerated from scripts/wrapper-contract.json. Do not hand-edit this task map.\n\n"
        "Select one task. Open its family CONTEXT.md, then the matching canonical workflow.\n"
        "Do not load the other families.\n\n| Task / command | Workspace | Purpose |\n|---|---|---|\n"
        + table + "\n\nSetup: [setup/CONTEXT.md](setup/CONTEXT.md). Run state: [workflows/run.md](workflows/run.md).\n"
    )
    for workspace in dict.fromkeys(row["workspace"] for row in routes.values()):
        family = Path(workspace).parent.name
        members = {name: row for name, row in routes.items() if row["workspace"] == workspace}
        links = "\n".join(f"| `{name}` | [{Path(row['workflow']).name}]({Path(row['workflow']).name}) | {row['description']} |" for name, row in members.items())
        files[Path(workspace)] = (
            f"# {family.title()} workflows\n\nGenerated from scripts/wrapper-contract.json; procedures live in the linked files.\n\n"
            f"One job: route the requested {family} task.\n\n## Inputs\n"
            "- Working: output/{run-id}/request.md and the scope and source references it names.\n"
            "- Reference: one selected workflow below and its Load / Skip list.\n\n## Process\n"
            "Choose one row and follow [the run lifecycle](../run.md). Skip sibling procedures and unrelated records.\n\n"
            "| Command | Contract | Job |\n|---|---|---|\n" + links + "\n\n## Outputs\n"
            "The chosen workflow defines output/{run-id}/01_review.md, any declared artifacts, and 02_result.json.\n\n"
            "## Human check\nRead the workflow's exact review criteria and record review in output/{run-id}/review.json.\n"
        )
    for name, row in routes.items():
        body = (
            f"Read `AGENTS.md`, `CONTEXT.md`, `{row['workspace']}`, then `{row['workflow']}` "
            "from this repository or an installed workspace copy. Follow that workflow's Load / Skip list.\n\n"
            "Generated from `scripts/wrapper-contract.json`. Behavior belongs to the linked workflow; "
            "this pointer grants no approval.\n"
        )
        desc = json.dumps(row["description"], ensure_ascii=False)
        files[Path(f".agents/skills/{name}/SKILL.md")] = f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}"
        files[Path(f".claude/commands/{name}.md")] = f"---\ndescription: {desc}\n---\n\n{body}\n$ARGUMENTS\n"
    return files


def render(root=ROOT, check=False):
    files = expected(root)
    actual = set(p.relative_to(root) for p in (root / ".agents/skills").glob("*/SKILL.md"))
    actual |= set(p.relative_to(root) for p in (root / ".claude/commands").glob("*.md"))
    extra = actual - set(files)
    problems = ["unexpected generated wrapper: " + str(p) for p in sorted(extra)]
    # Preflight every destination before changing any file. Unknown wrappers stay owned.
    for path in files:
        try:
            dest = safe_path(root, path)
            if dest.exists() and not dest.is_file():
                problems.append("wrapper destination is not a file: " + str(path))
        except ValueError as exc:
            problems.append(str(exc))
    if problems:
        return problems
    for path, content in files.items():
        dest = root / path
        if check:
            if not dest.is_file() or dest.read_text() != content:
                problems.append("wrapper drift: " + str(path))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", dir=dest.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(content)
                temporary.chmod(dest.stat().st_mode & 0o777 if dest.exists() else 0o644)
                os.replace(temporary, dest)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        errors = render(check=args.check)
    except (ValueError, OSError, TypeError) as exc:
        errors = [str(exc)]
    print("\n".join(errors) if errors else "Task maps, wrapper routes and generated surfaces match.")
    sys.exit(bool(errors))
