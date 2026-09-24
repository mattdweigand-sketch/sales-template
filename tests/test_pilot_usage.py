"""Pilot usage pdf pipeline: assemble from saved results, fail-closed reconciliation, local-only outputs."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PILOT = SCRIPTS / "pilot_usage"
POLICY = SCRIPTS.parents[0] / "_shared/policy.example.json"
sys.path.insert(0, str(PILOT))

from assemble_pilot_usage_input import assemble_input, load_marked_results  # noqa: E402
from compute_pilot_usage_report import compute_pilot_usage_report  # noqa: E402
from pilot_usage_local_storage import require_local_only_output_path  # noqa: E402
from pilot_usage_policy import load_pilot_usage_policy  # noqa: E402
from validate_pilot_usage_report import validate_computed_pilot_usage_report  # noqa: E402

SCOPE = "synthetic-project"


def _saved(calls: Path, suffix: str, marker: str, handle: str, columns, rows) -> None:
    (calls / f"input_{suffix}.json").write_text(json.dumps(
        {"tool_name": "analytics_query", "arguments": {"dataset": marker}}))
    (calls / f"output_{suffix}.json").write_text(json.dumps(
        {"tool": "analytics_query", "result": {"query_id": handle, "status": "running", "rows": None}}))
    (calls / f"output_{suffix}r0.json").write_text(json.dumps(  # running placeholder, must be ignored
        {"tool": "analytics_results",
         "result": {"query_id": handle, "status": "running", "columns": None, "rows": [], "row_count": 0}}))
    (calls / f"output_{suffix}r1.json").write_text(json.dumps(
        {"tool": "analytics_results",
         "result": {"query_id": handle, "status": "success", "columns": [{"name": c} for c in columns],
                    "rows": rows, "row_count": len(rows)}}))


class PilotUsagePdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = Path(self.temp.name) / "calls"
        self.calls.mkdir()
        self.policy = load_pilot_usage_policy(POLICY)
        self.policy["metric"]["enforce_allocation_limit"] = True
        _saved(self.calls, "a", "roster", "h1",
               ["USER_ID", "EMAIL"],
               [["a@example.org", "a@example.org"], ["b@example.org", "b@example.org"]])
        _saved(self.calls, "b", "allocations", "h4",
               ["EFFECTIVE_AT", "VOIDED_AT", "QUANTITY"],
               [["2026-08-12 10:00:00.000", None, "15000.000000"],
                ["2026-08-12 10:00:01.000", "2026-08-13 00:00:00.000", "500.000000"],
                ["2026-10-01 10:00:00.000", None, "15000.000000"]])
        _saved(self.calls, "c", "activities", "h5",
               ["ACTIVITY_ID", "USER_ID", "DATE", "QUANTITY", "ACTIVITY_TITLE"],
               [["ctx-1", "a@example.org", "2026-08-13", "100.5", "Draft a memo"],
                ["ctx-2", "a@example.org", "2026-08-20", "2.4999", None]])
        self.review = {
            "customer_name": "Test LLP", "scope_id": SCOPE, "prepared_by": "Seller",
            "pilot_start": "2026-08-12", "pilot_end": "2026-09-24", "data_through": "2026-09-20", "approved": True,
            "display_names": {"a@example.org": "A Person"},
            "categories": [{"category_id": "drafting", "label": "Drafting", "description": "Memos."}],
            "activity_categories": {"ctx-1": "drafting"},
            "narratives": {"scope_note": "s", "usage_highlights": [], "representative_work": [],
                           "work_interpretation": [], "business_value": [], "source_note": "src"},
        }

    def _input(self):
        return assemble_input(load_marked_results(self.calls), self.review, self.policy)

    def test_assemble_uses_final_result_and_reconciles(self) -> None:
        normalized = self._input()
        self.assertEqual(normalized["report"]["pilot_start"], "2026-08-12")
        self.assertEqual(normalized["report"]["allocated_units"], 15000)  # voided and future rows dropped
        self.assertEqual([s["usage_units"] for s in normalized["activities"]], [101, 2])  # half up per activity
        self.assertEqual(normalized["activities"][1]["category_id"], self.policy["uncategorized_category_id"])
        self.assertEqual(normalized["roster"][0]["display_name"], "A Person")
        self.assertEqual(normalized["roster"][1]["display_name"], "b")
        report = compute_pilot_usage_report(normalized, self.policy)
        self.assertEqual(report["headline"]["usage_units"], 103)
        self.assertEqual(validate_computed_pilot_usage_report(normalized, self.policy, report), [])

    def test_unapproved_review_fails_closed(self) -> None:
        self.review["approved"] = False
        with self.assertRaises(ValueError):
            compute_pilot_usage_report(self._input(), self.policy)

    def test_string_false_does_not_become_approval(self):
        self.review["approved"] = "false"
        with self.assertRaises(ValueError): self._input()

    def test_duplicate_activities_and_fractional_usage_units_rejected(self):
        normalized = self._input()
        normalized["activities"].append(copy.deepcopy(normalized["activities"][0]))
        with self.assertRaises(ValueError): compute_pilot_usage_report(normalized, self.policy)
        normalized = self._input()
        normalized["activities"][0]["usage_units"] = 1.5
        with self.assertRaises(ValueError): compute_pilot_usage_report(normalized, self.policy)

    def test_unknown_user_and_outside_window_rejected(self):
        normalized = self._input(); normalized["activities"][0]["user_id"] = "unknown@example.org"
        with self.assertRaises(ValueError): compute_pilot_usage_report(normalized,self.policy)
        normalized = self._input(); normalized["activities"][0]["date"] = "2027-01-01"
        with self.assertRaises(ValueError): compute_pilot_usage_report(normalized,self.policy)

    def test_incomplete_analytics_partitions_rejected(self):
        path = self.calls / "output_cr1.json"; doc=json.loads(path.read_text())
        doc["result"]["page_count"]=2;path.write_text(json.dumps(doc))
        with self.assertRaises(RuntimeError): load_marked_results(self.calls)

    def test_internal_participant_and_activity_excluded(self):
        results = load_marked_results(self.calls)
        results["roster"].append({"user_id":"staff@example.com","email":"staff@example.com"})
        results["activities"].append({"user_id":"staff@example.com","quantity":"300"})
        normalized = assemble_input(results,self.review,self.policy)
        self.assertEqual(len(normalized["roster"]),2)
        self.assertEqual(len(normalized["activities"]),2)

    def test_allowed_run_output_and_factory_symlink_rejected(self):
        self.assertTrue(require_local_only_output_path(SCRIPTS.parents[0]/"output/synthetic/report.pdf"))
        link = Path(self.temp.name)/"factory-link"
        link.symlink_to(SCRIPTS.parents[0],target_is_directory=True)
        with self.assertRaises(ValueError): require_local_only_output_path(link/"report.pdf")

    def test_usage_units_over_required_allocation_fails_closed(self) -> None:
        normalized = self._input()
        normalized["report"]["allocated_units"] = 50
        with self.assertRaises(ValueError):
            compute_pilot_usage_report(normalized, self.policy)

    def test_tampered_report_fails_validation(self) -> None:
        normalized = self._input()
        report = compute_pilot_usage_report(normalized, self.policy)
        tampered = copy.deepcopy(report)
        tampered["headline"]["usage_units"] += 1
        self.assertTrue(validate_computed_pilot_usage_report(normalized, self.policy, tampered))

    def test_missing_marker_is_an_error(self) -> None:
        for path in self.calls.glob("*_c*.json"):
            path.unlink()
        with self.assertRaises(RuntimeError):
            load_marked_results(self.calls)

    def test_output_inside_reusable_workspace_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            require_local_only_output_path(SCRIPTS.parents[0] / "out.pdf")
        self.assertTrue(require_local_only_output_path(Path(self.temp.name) / "out.pdf"))

    def test_cli_assemble_writes_input(self) -> None:
        review_path = Path(self.temp.name) / "review.json"
        review_path.write_text(json.dumps(self.review))
        out = Path(self.temp.name) / "out" / "input.json"
        result = subprocess.run(
            [sys.executable, str(PILOT / "assemble_pilot_usage_input.py"), "--review", str(review_path),
             "--policy", str(POLICY), "--output", str(out), "--tool-calls", str(self.calls)],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["activities"], 2)
        self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
