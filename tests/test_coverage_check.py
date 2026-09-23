"""Source-port coverage scenarios, extended to Friday and forecast failures."""
from pathlib import Path
from datetime import datetime
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from coverage_check import check, load_queries


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = Path(self.temp.name)
        self.policy = json.loads((ROOT/"_shared/policy.example.json").read_text())
        self.since = datetime.fromisoformat("2026-09-23T09:00:00+00:00")
        self.owner = self.policy["identity"]["owner_id"]
        self.opp = {"Id":"o1", "AccountId":"a1", "Account":{"Name":"Example Buyer"},
            "StageName":"S2", "Amount":100, "CloseDate":"2026-09-30", "OwnerId":self.owner,"IsClosed":False}
        self.contact = {"Id":"c1","AccountId":"a1","Email":"buyer@example.org"}

    def pair(self, name, source, records, selection, **extra):
        args = {"query_id":name,"source":source,"selection":selection,"owner_id":self.owner,
                "provider_query":"Synthetic issued query", **extra}
        result = {"status":"success","records":records,"total_count":len(records),
                  "next_cursor":None,"provider_reference":"synthetic-raw-receipt"}
        (self.calls/f"input_{name}.json").write_text(json.dumps({"started_at":self.since.isoformat(),"arguments":args}))
        (self.calls/f"output_{name}.json").write_text(json.dumps({"completed_at":self.since.isoformat(),"result":result}))

    def change(self, prefix, name, section, **values):
        path = self.calls/f"{prefix}_{name}.json"
        doc = json.loads(path.read_text()); doc[section].update(values); path.write_text(json.dumps(doc))

    def ready(self, scope="pipeline-daily", opps=None):
        self.pair("opps","crm",[self.opp] if opps is None else opps,"all_owned_open",object="Opportunity")
        for obj, rows in (("Contact",[self.contact]),("Task",[]),("Event",[])):
            self.pair(obj,"crm",rows,"linked_accounts_and_opportunities",object=obj,
                account_ids=["a1"], opportunity_ids=["o1"], fields=["StartDateTime","EndDateTime"])
        if scope == "pipeline-daily":
            self.pair("mail","mail",[],"external_inbox",start_date="2026-09-22",exclude_domains=["example.com"])
        else:
            self.pair("mail","mail",[],"account_inbound",start_date="2026-07-01",domains=["example.org"])
        self.pair("calendar","calendar",[],"account_calendar",account_ids=["a1"],start_date="2026-08-01",end_date="2026-11-01")
        if scope == "forecast":
            self.pair("booked","crm",[],"booked_in_quarter",object="Opportunity",start_date="2026-07-01",end_date="2026-10-01")

    def result(self, scope="pipeline-daily"):
        return check(self.calls,self.policy,self.since,scope)

    def test_complete_daily_friday_forecast(self):
        for scope in ("pipeline-daily","pipeline","forecast"):
            self.ready(scope)
            result = self.result(scope)
            self.assertTrue(result["ready"],result["errors"])
            self.assertEqual(result["open_count"],1)

    def test_missing_output_blocks_every_mode(self):
        for scope in ("pipeline-daily","pipeline","forecast"):
            self.ready(scope); (self.calls/"output_calendar.json").unlink()
            self.assertFalse(self.result(scope)["ready"])

    def test_failed_result_is_not_checked(self):
        self.ready(); self.change("output","mail","result",status="failed",error="timeout")
        self.assertFalse(self.result()["ready"])

    def test_incomplete_pagination_blocks(self):
        self.ready(); self.change("output","mail","result",next_cursor="p2")
        self.assertFalse(self.result()["ready"])

    def test_returned_cursor_completes_search(self):
        self.ready(); self.change("output","mail","result",next_cursor="p2")
        self.pair("mail2","mail",[],"external_inbox",start_date="2026-09-22",exclude_domains=["example.com"],cursor="p2")
        self.change("input","mail2","arguments",query_id="mail")
        self.assertTrue(self.result()["ready"],self.result()["errors"])

    def test_unreturned_cursor_blocks(self):
        self.ready(); self.pair("mail2","mail",[],"external_inbox",start_date="2026-09-22",exclude_domains=["example.com"],cursor="invented")
        self.change("input","mail2","arguments",query_id="mail")
        self.assertFalse(self.result()["ready"])

    def test_no_external_domain_and_wrong_calendar_account(self):
        self.contact["Email"]="internal@example.com"; self.ready()
        self.change("input","calendar","arguments",account_ids=["unrelated"])
        result = self.result()
        self.assertFalse(result["ready"])
        self.assertEqual(result["mail_covered"],0); self.assertEqual(result["calendar_covered"],0)

    def test_event_fields_and_calendar_range_required(self):
        self.ready(); self.change("input","Event","arguments",fields=["Subject"])
        self.change("input","calendar","arguments",end_date="2026-09-24")
        self.assertFalse(self.result()["ready"])

    def test_filtered_inbox_does_not_satisfy_daily(self):
        self.ready(); self.change("input","mail","arguments",domains=["example.org"])
        self.assertFalse(self.result()["ready"])

    def test_domain_matches_only_return_actual_receipts(self):
        self.ready()
        rows=[{"email_id":"match","from_":"buyer@example.org"},{"email_id":"other","from_":"someone@example.net"}]
        self.change("output","mail","result",records=rows,total_count=2)
        self.assertEqual([x["email_id"] for x in self.result()["matched_mail"]],["match"])

    def test_successful_empty_scope_is_valid(self):
        self.ready(opps=[])
        self.assertTrue(self.result()["ready"],self.result()["errors"])

    def test_prior_run_is_not_evidence(self):
        self.ready()
        path=self.calls/"input_calendar.json"; doc=json.loads(path.read_text())
        doc["started_at"]="2026-09-22T09:00:00Z";path.write_text(json.dumps(doc))
        self.assertFalse(self.result()["ready"])

    def test_count_mismatch_blocks(self):
        self.ready(); self.change("output","opps","result",total_count=2)
        self.assertFalse(self.result()["ready"])

    def test_next_quarter_all_amount_candidates_in_scope(self):
        self.opp["CloseDate"]="2026-12-31";self.ready("forecast")
        self.assertEqual(self.result("forecast")["in_scope"],1)
        self.change("output","booked","result",status="failed")
        self.assertFalse(self.result("forecast")["ready"])

    def test_closed_wrong_owner_and_unknown_date_not_silently_accepted(self):
        self.opp.update(OwnerId="other",IsClosed=True,CloseDate="not-a-date")
        self.ready("forecast")
        self.assertFalse(self.result("forecast")["ready"])

    def test_recovered_error_kept_in_raw_does_not_contaminate_success(self):
        raw=self.calls/"raw";raw.mkdir();(raw/"failed.json").write_text('{"error":"temporary failure"}')
        self.ready();self.assertTrue(self.result()["ready"])
