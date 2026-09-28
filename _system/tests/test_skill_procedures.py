"""Every procedure, reference, and contract names only things that exist.

A saved project skill points to `workflows/<name>/CONTEXT.md`, then its procedure.
This test resolves what the repo's markdown references:

- every `policy.<dotted>` key against _shared/policy.yaml
- every `rules#<anchor>` against the anchors defined in _shared/rules.md
- every backticked `_shared/...`, `workflows/...` path against the checkout
- every `<script>.py` named in markdown against _shared/scripts/ and workflow scripts/
- every `policy.tooling.scripts` path exists
- every root route has a CONTEXT.md with cadence, reads, writes, next frontmatter
- every rules.md anchor is cited by at least two skill folders (a one-skill rule belongs in that skill)
- no file still cites the retired `skills/` root, cadence folders, or `domains/` layer

A cite that does not resolve fails here instead of at run time.
"""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "_shared"
WORKFLOWS = ROOT / "workflows"
CADENCE_VALUES = {"daily", "weekly", "one-off"}
FIXTURES = ROOT / "tests" / "fixtures"

POLICY_REF = re.compile(r"(?<![A-Za-z0-9_])policy\.((?!(?:example\.)?yaml\b)[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)")
RULE_REF = re.compile(r"rules#([a-z_]+)")
RULE_DEF = re.compile(r'<a id="([a-z_]+)"></a>')
REPO_PATH = re.compile(r"`((?:_shared|workflows)/[A-Za-z0-9_./<>-]+)`")
SCRIPT_REF = re.compile(r"`([a-z_]+\.py)`")
AGENTS_ROW = re.compile(r"^\| `([a-z-]+)` \| `([^`]+)` \|", re.M)

# Policy sub-keys that procedures name in prose but that are dict members, list items, or
# placeholders rather than keys. Add here only with the reason.
POLICY_ALLOW = set()


def markdown_files():
    files = [ROOT / "AGENTS.md", ROOT / "CONTEXT.md", SHARED / "rules.md", SHARED / "CONTEXT.md",
             SHARED / "scripts" / "CONTEXT.md"]
    files.extend(sorted(WORKFLOWS.rglob("*.md")))
    return [f for f in files if f.exists()]


def skill_dirs():
    return sorted(d for d in WORKFLOWS.iterdir() if d.is_dir())


def body_after_frontmatter(text):
    if text.startswith("---\n"):
        return text.split("---\n", 2)[2].lstrip("\n")
    return text


def frontmatter(text):
    if not text.startswith("---\n"):
        return None
    return yaml.safe_load(text.split("---\n", 2)[1])


def policy_has(policy, dotted):
    cur = policy
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


class SkillProcedureReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = yaml.safe_load((SHARED / "policy.example.yaml").read_text())
        cls.rules_text = (SHARED / "rules.md").read_text()
        cls.anchors = set(RULE_DEF.findall(cls.rules_text))
        cls.scripts = {p.name for p in (SHARED / "scripts").rglob("*.py")} | {p.name for p in WORKFLOWS.rglob("scripts/**/*.py")}
        cls.files = markdown_files()

    def test_flat_workflows_layout(self):
        self.assertEqual([d.name for d in skill_dirs()], ["close", "forecast-weekly", "interaction-sync", "pilot-usage",
                                                          "pipeline-review", "sales-call-prep", "task-triage-speed-run"])
        for d in skill_dirs():
            self.assertTrue((d / "CONTEXT.md").is_file(), f"{d.name}/CONTEXT.md missing")
            self.assertTrue((d / "references/procedure.md").is_file(), f"{d.name}: procedure missing")
        self.assertEqual(sorted(p.name for p in ROOT.glob("[0-9][0-9]_*")), [], "retired cadence folders remain")
        self.assertFalse((ROOT / "domains").exists(), "retired domains/ layer remains")

    def test_script_registry_paths_exist(self):
        missing = [f"{k}: {v}" for k, v in self.policy["tooling"]["scripts"].items() if not (ROOT / v).is_file()]
        self.assertEqual(missing, [])

    def test_policy_keys_resolve(self):
        missing = []
        for f in self.files:
            for key in set(POLICY_REF.findall(f.read_text())):
                if key in POLICY_ALLOW or policy_has(self.policy, key):
                    continue
                missing.append(f"{f.relative_to(ROOT)}: policy.{key}")
        self.assertEqual(missing, [])

    def test_rule_anchors_resolve(self):
        missing = []
        for f in self.files:
            for a in set(RULE_REF.findall(f.read_text())):
                if a not in self.anchors:
                    missing.append(f"{f.relative_to(ROOT)}: rules#{a}")
        self.assertEqual(missing, [])

    def test_repo_paths_resolve(self):
        missing = []
        for f in self.files:
            text = f.read_text()
            for p in set(REPO_PATH.findall(text)):
                if "<" in p:
                    continue  # pattern like workflows/<name>/
                target = ROOT / p
                if f.parent != ROOT and not target.exists():
                    target = (f.parent / p).resolve()
                if p in {"_shared/policy.yaml", "_shared/adapters.json"}:
                    target = SHARED / ("policy.example.yaml" if p.endswith("yaml") else "adapters.example.json")
                if not target.exists():
                    missing.append(f"{f.relative_to(ROOT)}: {p}")
        self.assertEqual(missing, [])

    def test_relative_contract_paths_resolve(self):
        missing = []
        for c in (ROOT, SHARED):
            text = (c / "CONTEXT.md").read_text()
            for p in set(re.findall(r"`(\.\./[A-Za-z0-9_./-]+|[a-z-]+/[A-Za-z0-9_./-]+\.md)`", text)):
                if not (c / p).resolve().exists():
                    missing.append(f"{c.name}/CONTEXT.md: {p}")
        self.assertEqual(missing, [])

    def test_scripts_resolve(self):
        missing = []
        for f in self.files:
            for s in set(SCRIPT_REF.findall(f.read_text())):
                if s not in self.scripts:
                    missing.append(f"{f.relative_to(ROOT)}: {s}")
        self.assertEqual(missing, [])

    def test_route_table_matches_folders(self):
        catalog = (ROOT / "CONTEXT.md").read_text()
        rows = dict(re.findall(r'^\| `([a-z-]+)` \| \[.*?\]\(([^)]+)\)', catalog, re.M))
        folders = {d.name: f"workflows/{d.name}/CONTEXT.md" for d in skill_dirs()}
        self.assertEqual(rows, folders)
        for body in rows.values():
            self.assertTrue((ROOT / body).exists(), body)

    def test_procedure_frontmatter(self):
        for d in skill_dirs():
            fm = frontmatter((d / "CONTEXT.md").read_text())
            self.assertIsNotNone(fm, f"{d.name}: no frontmatter")
            self.assertEqual(set(fm), {"cadence", "reads", "writes", "next"}, d.name)
            self.assertIn(fm["cadence"], CADENCE_VALUES, d.name)

    def test_reads_declares_every_cited_policy_block(self):
        """The `reads` frontmatter names every top-level policy block the skill folder cites directly."""
        gaps = []
        for d in skill_dirs():
            text = (d / "CONTEXT.md").read_text()
            fm = frontmatter(text)
            m = re.search(r"_shared/policy\.yaml \(([^)]*)\)", fm["reads"])
            declared = {b.strip() for b in m.group(1).split(",")} if m else set()
            cited = {k.split(".")[0] for p in d.rglob("*.md") for k in POLICY_REF.findall(p.read_text())}
            missing = sorted(cited - declared)
            if missing:
                gaps.append(f"{d.name}: reads omits {missing}")
        self.assertEqual(gaps, [])

    def test_every_rule_is_shared(self):
        cited_by = {a: set() for a in self.anchors}
        for d in skill_dirs():
            text = "\n".join(p.read_text() for p in d.rglob("*.md"))
            for a in set(RULE_REF.findall(text)):
                if a in cited_by:
                    cited_by[a].add(d.name)
        lonely = sorted(f"rules#{a} cited by {sorted(s)}" for a, s in cited_by.items() if len(s) < 2)
        self.assertEqual(lonely, [])

    def test_no_retired_skills_root(self):
        stale = []
        scripts = sorted((SHARED / "scripts").rglob("*.py")) + sorted(WORKFLOWS.rglob("*.py"))
        for f in list(self.files) + [ROOT / "_shared" / "policy.example.yaml"] + scripts:
            if FIXTURES in f.parents or f == Path(__file__).resolve():
                continue
            text = f.read_text()
            if re.search(r"(?<![A-Za-z0-9_/.-])skills/", text) or re.search(r"\b0[123]_(daily|weekly|one-off)\b", text) or re.search(r"(?<![A-Za-z0-9_/.-])domains/", text):
                stale.append(str(f.relative_to(ROOT)))
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
