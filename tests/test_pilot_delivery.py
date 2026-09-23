"""Optional end-to-end PDF test through real helper CLIs and an installed renderer."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "scripts/pilot_usage"


@unittest.skipUnless(os.environ.get("PILOT_PDF_RENDERER") and importlib.util.find_spec("pypdf"),
                     "set PILOT_PDF_RENDERER and install optional PDF requirements")
class PilotDeliveryTests(unittest.TestCase):
    def test_full_pipeline_creates_two_complete_letter_pages(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            review = json.loads((ROOT/"examples/pilot-usage/narrative-review.json").read_text())
            review["approved"] = True  # synthetic fixture authorization only
            (out/"narrative-review.json").write_text(json.dumps(review))
            def run(script, *args):
                result = subprocess.run([sys.executable, str(PILOT/script), "--policy",
                    str(ROOT/"_shared/policy.example.json"), *map(str,args)], capture_output=True, text=True)
                if result.returncode:
                    raise subprocess.CalledProcessError(result.returncode,result.args,result.stdout,result.stderr)
                return result
            run("assemble_pilot_usage_input.py", "--review",out/"narrative-review.json","--results",
                ROOT/"examples/pilot-usage/results.json","--output",out/"input.json")
            run("compute_pilot_usage_report.py","--input",out/"input.json","--output",out/"report.json")
            result = run("validate_pilot_usage_report.py","--input",out/"input.json","--report",out/"report.json")
            self.assertTrue(json.loads(result.stdout)["valid"])
            run("render_pilot_usage_report.py","--input",out/"input.json","--report",out/"report.json","--output",out/"report.html")
            run("print_pilot_usage_pdf.py","--html",out/"report.html","--output",out/"report.pdf",
                "--renderer",os.environ["PILOT_PDF_RENDERER"])
            pdf = PdfReader(out/"report.pdf")
            self.assertEqual(len(pdf.pages),2)
            self.assertTrue(all((float(p.mediabox.width),float(p.mediabox.height)) == (612,792) for p in pdf.pages))
            text = " ".join(" ".join(p.extract_text() for p in pdf.pages).split())
            for expected in ("Example Company", "Page 1 of 2", "Page 2 of 2", "financial return", "human review"):
                self.assertIn(expected,text)
            self.assertNotIn("Prepare a sourced market brief",text)  # raw task title never printed
            prior = (out/"report.pdf").read_bytes()
            with self.assertRaises(subprocess.CalledProcessError):
                run("print_pilot_usage_pdf.py","--html",out/"missing.html","--output",out/"report.pdf",
                    "--renderer",os.environ["PILOT_PDF_RENDERER"])
            self.assertEqual((out/"report.pdf").read_bytes(),prior)
