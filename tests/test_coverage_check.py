"""Source coverage checks for daily, extended and forecast runs."""
from pathlib import Path
from datetime import datetime
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from coverage_check import check, load_queries, reference_path


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
                "provider_query":"Synthetic issued query", "cursor":None, **extra}
        result = {"status":"success","records":records,"total_count":len(records),
                  "next_cursor":None,"provider_reference":f"raw_{name}.json"}
        (self.calls/f"raw_{name}.json").write_text(json.dumps({"records":records}))
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
            self.pair("mail","mail",[],"external_inbox",start_date="2026-09-22",end_date=None,exclude_domains=["example.com"])
        else:
            self.pair("mail","mail",[],"account_inbound",start_date="2026-07-01",end_date=None,domains=["example.org"])
        self.pair("calendar","calendar",[],"account_calendar",account_ids=["a1"],start_date="2026-08-01",end_date="2026-11-01")
        if scope == "forecast":
            self.pair("booked","crm",[],"booked_in_quarter",object="Opportunity",start_date="2026-07-01",end_date="2026-10-01")

    def result(self, scope="pipeline-daily"):
        return check(self.calls,self.policy,self.since,scope)

    def test_complete_daily_extended_forecast(self):
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
        self.pair("mail2","mail",[],"external_inbox",start_date="2026-09-22",end_date=None,exclude_domains=["example.com"],cursor="p2")
        self.change("input","mail2","arguments",query_id="mail")
        self.assertTrue(self.result()["ready"],self.result()["errors"])

    def test_unreturned_cursor_blocks(self):
        self.ready(); self.pair("mail2","mail",[],"external_inbox",start_date="2026-09-22",end_date=None,exclude_domains=["example.com"],cursor="invented")
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
        rows=[{"email_id":key,"thread_id":"t1","date":"2026-09-23T09:00:00Z","from_":sender} for key,sender in [("match","buyer@example.org"),("other","someone@example.net")]]
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


    def test_unknown_stages_preserve_open_count_and_block_scope(self):
        for stage in (None, "", "  ", 4, "Unmapped native stage"):
            with self.subTest(stage=stage):
                self.opp["StageName"] = stage
                self.ready()
                result = self.result()
                self.assertFalse(result["ready"])
                self.assertEqual(result["open_count"], 1)
                self.assertEqual(result["unresolved_scope"], ["o1"])
        del self.opp["StageName"]
        self.ready()
        self.assertFalse(self.result()["ready"])

    def test_recognized_exclusion_and_configured_custom_stage(self):
        self.opp["StageName"] = "S0"
        self.ready()
        self.assertTrue(self.result()["ready"])
        self.assertEqual(self.result()["in_scope_ids"], [])
        self.policy["pipeline"]["stage_order"].append("CUSTOM")
        self.policy["pipeline"]["in_scope_stages"].append("CUSTOM")
        self.opp["StageName"] = "CUSTOM - Buyer evaluation"
        self.ready()
        self.assertTrue(self.result()["ready"])
        self.assertEqual(self.result()["in_scope_ids"], ["o1"])

    def test_invalid_scope_policy_fails_as_an_error(self):
        self.ready()
        self.policy["pipeline"]["in_scope_stages"] = ["absent"]
        self.assertFalse(self.result()["ready"])
        self.assertIn("policy:", self.result()["errors"][0])

    def test_each_mode_rejects_bad_mail_intervals_and_narrowing(self):
        for scope in ("pipeline-daily", "pipeline", "forecast"):
            for end in ("2026-07-02", "2026-09-22", "not-a-date"):
                with self.subTest(scope=scope,end=end):
                    self.ready(scope)
                    self.change("input","mail","arguments",end_date=end)
                    self.assertFalse(self.result(scope)["ready"])
            self.ready(scope)
            path=self.calls/"input_mail.json";doc=json.loads(path.read_text())
            del doc["arguments"]["end_date"];path.write_text(json.dumps(doc))
            self.assertFalse(self.result(scope)["ready"])
            self.ready(scope)
            self.change("input","mail","arguments",extra_filters=["subject contains unrelated phrase"])
            self.assertFalse(self.result(scope)["ready"])
            self.ready(scope)
            self.change("input","mail","arguments",end_date="2026-09-24",fields=["body_text"],page_size=100)
            self.assertTrue(self.result(scope)["ready"],self.result(scope)["errors"])

    def test_calendar_selection_and_inclusive_last_day(self):
        self.ready()
        self.change("input","calendar","arguments",selection="selected_events")
        self.assertFalse(self.result()["ready"])
        self.ready()
        self.change("input","calendar","arguments",end_date="2026-10-23")
        self.assertFalse(self.result()["ready"])
        self.change("input","calendar","arguments",end_date="2026-10-24")
        self.assertTrue(self.result()["ready"],self.result()["errors"])

    def test_domain_case_and_superset(self):
        self.ready("pipeline")
        self.change("input","mail","arguments",domains=["EXAMPLE.ORG","extra.org"])
        self.assertTrue(self.result("pipeline")["ready"])
        self.ready()
        self.change("input","mail","arguments",exclude_domains=["EXAMPLE.COM"])
        self.assertTrue(self.result()["ready"])

    def test_malformed_rows_and_boolean_count_have_context(self):
        for rows, total in (([None],1),([4],1),([{"Id":[]}],1),([self.opp],True)):
            self.ready()
            self.change("output","opps","result",records=rows,total_count=total)
            result=self.result()
            self.assertFalse(result["ready"])
            self.assertTrue(any("input_opps.json" in error for error in result["errors"]))

    def test_explicit_terminal_and_initial_cursor_required(self):
        for prefix,section,key in (("input","arguments","cursor"),("output","result","next_cursor")):
            self.ready()
            path=self.calls/f"{prefix}_mail.json";doc=json.loads(path.read_text())
            del doc[section][key];path.write_text(json.dumps(doc))
            self.assertFalse(self.result()["ready"])

    def test_missing_raw_evidence_and_reference_escape_block(self):
        self.ready();(self.calls/"raw_mail.json").unlink()
        self.assertFalse(self.result()["ready"])
        self.ready();self.change("output","mail","result",provider_reference="../../outside.json")
        self.assertFalse(self.result()["ready"])
        link=self.calls/"linked.json";link.symlink_to(self.calls/"raw_mail.json")
        self.change("output","mail","result",provider_reference="linked.json")
        self.assertFalse(self.result()["ready"])

    def test_malformed_sender_attendee_and_account(self):
        self.ready()
        row={"email_id":"m1","thread_id":"t1","date":"2026-09-23T09:00:00Z","from_":["buyer@example.org"]}
        self.change("output","mail","result",records=[row],total_count=1)
        self.assertFalse(self.result()["ready"])
        self.ready()
        self.change("output","calendar","result",records=[{"event_id":"e1","attendees":[None]}],total_count=1)
        self.assertFalse(self.result()["ready"])
        self.ready();self.change("output","opps","result",records=[dict(self.opp,AccountId=[])])
        self.assertFalse(self.result()["ready"])

    def test_cycle_changed_selection_and_changed_total_fail(self):
        for mutation in ("cycle", "selection", "total"):
            self.ready()
            self.change("output","mail","result",next_cursor="p2")
            self.pair("mail2","mail",[],"external_inbox",start_date="2026-09-22",end_date=None,
                exclude_domains=["example.com"],cursor="p2")
            self.change("input","mail2","arguments",query_id="mail")
            if mutation == "cycle":self.change("output","mail2","result",next_cursor="p2")
            elif mutation == "selection":self.change("input","mail2","arguments",start_date="2026-09-21")
            else:self.change("output","mail2","result",total_count=1)
            self.assertFalse(self.result()["ready"])

    def test_booked_scope_flags_and_open_overlap(self):
        row={"Id":"won-1","OwnerId":self.owner,"IsClosed":True,"IsWon":True,"CloseDate":"2026-09-01","Amount":100}
        for changes in ({"IsClosed":False},{"IsWon":None},{"OwnerId":"other"},{"CloseDate":"invalid"},{"Id":"o1"}):
            self.ready("forecast")
            self.change("output","booked","result",records=[dict(row,**changes)],total_count=1)
            self.assertFalse(self.result("forecast")["ready"])
        self.ready("forecast")
        self.change("output","booked","result",records=[row],total_count=1)
        self.assertEqual(self.result("forecast")["booked_ids"],["won-1"])
        self.assertTrue(self.result("forecast")["ready"])

    def test_missing_start_and_invalid_forecast_amount_do_not_establish_scope(self):
        self.ready()
        path=self.calls/"input_mail.json";doc=json.loads(path.read_text())
        del doc["arguments"]["start_date"];path.write_text(json.dumps(doc))
        self.assertFalse(self.result()["ready"])
        for amount in (False,"100",float("inf")):
            self.opp["Amount"]=amount;self.ready("forecast")
            self.assertFalse(self.result("forecast")["ready"])
        del self.opp["Amount"];self.ready("forecast")
        self.assertEqual(self.result("forecast")["unresolved_scope"],["o1"])

    def test_crm_snapshot_narrowing_and_incomplete_calendar_addresses_fail(self):
        self.ready()
        self.change("input","opps","arguments",extra_filters=["Amount > 500000"])
        self.assertFalse(self.result()["ready"])
        self.ready()
        self.change("input","calendar","arguments",addresses=["unrelated@example.net"])
        self.assertFalse(self.result()["ready"])
        self.change("input","calendar","arguments",addresses=["BUYER@example.org","unrelated@example.net"])
        self.assertTrue(self.result()["ready"],self.result()["errors"])
