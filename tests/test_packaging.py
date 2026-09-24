"""Regression checks for real Git inventories, safe generation and clean exports."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_repo
import wrappers

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "output", "__pycache__", ".venv", ".env", ".env.*", "policy.json", "adapters.md"))
        wrappers.render(self.root)

    def git(self, *args, root=None):
        return subprocess.run(["git", *args], cwd=root or self.root, check=True, capture_output=True, text=True)

    def initialize(self, separate=False):
        args = ["init", "-q"]
        if separate:
            args.append("--separate-git-dir=" + str(self.parent / "git-metadata"))
        self.git(*args)
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic test", "-c", "user.email=test@example.com", "commit", "-qm", "Synthetic fixture")

    def test_git_modes_reject_staged_private_material(self):
        self.initialize()
        worktree = self.parent / "worktree"
        self.git("worktree", "add", "--detach", str(worktree), "HEAD")
        for root in (self.root, worktree):
            for name in ("_shared/policy.json", "_shared/adapters.md", "output/run/private.json"):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("{}\n")
                self.git("add", "-f", name, root=root)
            errors, _ = check_repo.check(root)
            for name in ("_shared/policy.json", "_shared/adapters.md", "output/run/private.json"):
                self.assertIn("deployment or runtime material included: " + name, errors)

    def test_separate_git_directory_and_ignored_untracked_config(self):
        self.initialize(separate=True)
        private = self.root / "_shared/policy.json"
        private.write_text("{}\n")
        self.assertNotIn(Path("_shared/policy.json"), check_repo.public_files(self.root))
        self.git("add", "-f", "_shared/policy.json")
        self.assertIn(Path("_shared/policy.json"), check_repo.public_files(self.root))

    def test_export_inside_unrelated_repo_does_not_scan_parent(self):
        self.git("init", "-q", root=self.parent)
        (self.parent / "parent-only.md").write_text("Do not inspect this file as part of the export.\n")
        files = check_repo.public_files(self.root)
        self.assertIn(Path("AGENTS.md"), files)
        self.assertNotIn(Path("parent-only.md"), files)
        self.assertFalse(any(str(path).startswith("repo/") for path in files))

    def test_broken_git_and_unexpected_discovery_failures_do_not_fallback(self):
        (self.root / ".git").write_text("gitdir: missing-metadata\n")
        with self.assertRaises(ValueError):
            check_repo.public_files(self.root)
        (self.root / ".git").unlink()
        failure = subprocess.CompletedProcess([], 128, "", "fatal: permission denied")
        with mock.patch.object(check_repo.subprocess, "run", return_value=failure):
            with self.assertRaises(ValueError):
                check_repo.public_files(self.root)

    def test_ancestor_and_leaf_symlinks_never_modify_any_destination(self):
        for relative in (".agents/skills", ".agents/skills/forecast-weekly", ".claude/commands", ".claude/commands/forecast-weekly.md", "workflows/revenue"):
            with self.subTest(path=relative):
                root = self.parent / ("fixture-" + relative.replace("/", "-").replace(".", ""))
                shutil.copytree(self.root, root)
                target = root / relative
                outside = self.parent / (root.name + "-outside")
                shutil.move(target, outside)
                target.symlink_to(outside, target_is_directory=outside.is_dir())
                sentinel = outside / "sentinel.txt" if outside.is_dir() else outside
                sentinel.write_text("preserve external content\n")
                (root / "CONTEXT.md").write_text("preserve all earlier destinations\n")
                try:
                    self.assertTrue(wrappers.render(root))
                except ValueError as exc:
                    self.assertIn("symlink", str(exc))
                self.assertEqual(sentinel.read_text(), "preserve external content\n")
                self.assertEqual((root / "CONTEXT.md").read_text(), "preserve all earlier destinations\n")

    def test_unknown_wrapper_is_retained_without_partial_generation(self):
        unknown = self.root / ".claude/commands/custom.md"
        unknown.write_text("owned elsewhere\n")
        (self.root / "CONTEXT.md").write_text("keep until preflight passes\n")
        self.assertTrue(wrappers.render(self.root))
        self.assertEqual(unknown.read_text(), "owned elsewhere\n")
        self.assertEqual((self.root / "CONTEXT.md").read_text(), "keep until preflight passes\n")

    def test_clean_git_export_keeps_full_installation(self):
        self.initialize()
        (self.root / "_shared/policy.json").write_text("private deployment\n")
        (self.root / "output").mkdir()
        (self.root / "output/private.txt").write_text("private run\n")
        archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=self.root, check=True, capture_output=True).stdout
        export = self.parent / "export"
        export.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(export)
        for name in ("setup/CONTEXT.md", "examples/CONTEXT.md", "tests/CONTEXT.md", ".agents/skills/sales-call-prep/SKILL.md", ".claude/commands/sales-call-prep.md"):
            self.assertTrue((export / name).is_file())
        self.assertFalse((export / "_shared/policy.json").exists())
        self.assertFalse((export / "output").exists())
        self.assertFalse(list(export.rglob("*.pyc")))
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for command in (["scripts/check_repo.py"], ["scripts/runs.py", "init", "exported-001", "sales-call-prep"]):
            proc = subprocess.run([sys.executable, *command], cwd=export, capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
