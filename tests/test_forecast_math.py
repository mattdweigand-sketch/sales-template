import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from forecast_math import calculate

ROOT = Path(__file__).resolve().parents[1]


class ForecastMathTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "_shared/policy.example.json").read_text())
        self.data = {"quarter_start": "2026-07-01", "quarter_end": "2026-10-01", "target": "100", "rows": []}

    def row(self, deal_id, amount, bucket="commit", population="current"):
        return {"deal_id": deal_id, "population": population, "bucket": bucket,
                "amount": amount, "currency": "USD", "revenue_basis": "annual_contract_value",
                "source_refs": ["raw/" + deal_id + ".json"]}

    def test_selected_path_buffer_is_not_all_upside(self):
        self.data["rows"] = [self.row("c", "80"), self.row("u1", "50", "upside"), self.row("u2", "30", "upside"), self.row("pull", "900", None, "next")]
        out = calculate(self.data, self.policy)
        self.assertTrue(out["complete"])
        self.assertEqual(out["selected_ids"], ["u1"])
        self.assertEqual({k: out["totals"][k] for k in ("call", "path_total", "path_buffer", "all_upside_buffer")},
                         {"call": "80", "path_total": "130", "path_buffer": "30", "all_upside_buffer": "60"})

    def test_ties_and_insufficient_path(self):
        self.data["rows"] = [self.row("z", "10", "upside"), self.row("a", "10", "upside")]
        out = calculate(self.data, self.policy)
        self.assertEqual(out["selected_ids"], ["a", "z"])
        self.assertEqual(out["totals"]["uncovered_gap"], "80")

    def test_target_met_or_absent(self):
        self.data["rows"] = [self.row("c", "120"), self.row("u", "30", "upside")]
        out = calculate(self.data, self.policy)
        self.assertEqual(out["selected_ids"], [])
        self.assertEqual(out["totals"]["gap"], "-20")
        self.data["target"] = None
        out = calculate(self.data, self.policy)
        self.assertTrue(out["complete"])
        self.assertEqual(out["totals"]["call"], "120")
        self.assertTrue(all(out["totals"][k] is None for k in ("gap", "path_total", "all_upside_buffer")))

    def test_unknown_is_not_zero(self):
        self.data["rows"] = [self.row("known", "80"), self.row("missing", None, None, "booked")]
        out = calculate(self.data, self.policy)
        self.assertFalse(out["complete"])
        self.assertEqual(out["known_subtotals"]["call"], "80")
        self.assertIsNone(out["totals"]["call"])
        self.assertIsNone(out["totals"]["gap"])
        self.assertEqual(out["unknown_counts"]["booked"], 1)
        self.data["rows"][1] = self.row("missing", None, "upside")
        out = calculate(self.data, self.policy)
        self.assertEqual(out["totals"]["gap"], "20")
        self.assertIsNone(out["totals"]["path_total"])

    def test_exact_decimal_and_zero(self):
        self.data["target"] = "0.3"
        self.data["rows"] = [self.row("a", "0.1"), self.row("b", "0.2"), self.row("zero", "0")]
        out = calculate(self.data, self.policy)
        self.assertEqual(out["totals"]["call"], "0.3")
        self.assertEqual(out["totals"]["gap"], "0")
        self.assertEqual(out["unknown_counts"]["commit"], 0)

    def test_invalid_rows_and_amounts_are_errors(self):
        for bad in (None, [], "row", {"deal_id": True}):
            with self.subTest(row=bad):
                self.data["rows"] = [bad]
                self.assertTrue(calculate(self.data, self.policy)["errors"])
        self.assertTrue(calculate(self.data, {"reporting": None})["errors"])
        for amount in (True, 2.5, "NaN", "Infinity", "-1", "", "no amount"):
            with self.subTest(amount=amount):
                self.data["rows"] = [self.row("a", amount)]
                self.assertTrue(calculate(self.data, self.policy)["errors"])

    def test_duplicate_currency_basis_and_population_conflicts(self):
        base = self.row("a", "1")
        for field, value in (("deal_id", "a"), ("currency", "EUR"), ("revenue_basis", "monthly_recurring"), ("population", "next")):
            with self.subTest(field=field):
                other = self.row("b", "2")
                other[field] = value
                self.data["rows"] = [base, other]
                out = calculate(self.data, self.policy)
                self.assertFalse(out["complete"])
                self.assertTrue(out["errors"])


if __name__ == "__main__":
    unittest.main()
