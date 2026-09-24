"""Synthetic receipt, reply-classification and digest regression checks."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mail_contact_stats import contact_stats, kind_of
from mail_thread_digest import clean
from mail_evidence import load_messages, load_mail_evidence


def message(key, sender="seller@example.com", date="2026-09-20T12:00:00Z", kind=None, **extra):
    row = {"email_id":key,"thread_id":"thread-1","date":date,"from_":sender,
           "to":["buyer@example.org"],"subject":"An evaluation",**extra}
    if kind is not None:
        row["classification"]={"kind":kind,"basis":"content_review","evidence_refs":["source.json"]}
    return row


class MailTests(unittest.TestCase):
    def stats(self, rows, **kwargs):
        return contact_stats(rows,"seller@example.com",["example.com"],{"buyer@example.org"},
            complete=kwargs.pop("complete",True),history_complete=kwargs.pop("history_complete",True),**kwargs)[0]

    def test_reply_resets_unanswered_but_ooo_does_not(self):
        rows=[message("sent-1"),message("reply","buyer@example.org","2026-09-21T12:00:00Z",kind="substantive"),
              message("sent-2",date="2026-09-22T12:00:00Z"),
              message("ooo","buyer@example.org","2026-09-23T12:00:00Z",kind="ooo",subject="Automatic reply")]
        result=self.stats(rows)
        self.assertEqual(result["unanswered_count"],1)
        self.assertTrue(result["has_substantive_reply"])
        self.assertEqual(result["last_inbound_type"],"ooo")

    def test_ooo_sentence_is_unknown_until_reviewed(self):
        reply=message("reply","buyer@example.org","2026-09-21T12:00:00Z",
            body="I will be out of the office Friday, but please send the agreement today.")
        result=self.stats([message("sent"),reply])
        self.assertEqual(result["last_inbound_type"],"unknown")
        self.assertIsNone(result["unanswered_count"])
        self.assertIsNone(result["has_substantive_reply"])
        reply["classification"]={"kind":"substantive","basis":"content_review","evidence_refs":["source.json"]}
        self.assertEqual(self.stats([message("sent"),reply])["unanswered_count"],0)

    def test_later_unknown_blocks_interval_but_older_unknown_does_not(self):
        rows=[message("unknown","buyer@example.org"),
              message("reply","buyer@example.org","2026-09-21T12:00:00Z",kind="substantive"),
              message("sent",date="2026-09-22T12:00:00Z")]
        self.assertEqual(self.stats(rows)["unanswered_count"],1)
        rows.append(message("later","buyer@example.org","2026-09-23T12:00:00Z"))
        self.assertIsNone(self.stats(rows)["unanswered_count"])

    def test_relay_bounce_identified_recipient_without_using_bounce_thread(self):
        bounce=message("bounce","relay@example.net","2026-09-22T12:00:00Z",kind="bounce",
            subject="Delivery has failed",to=["seller@example.com"],thread_id="bounce-thread",
            delivery_failures=[{"recipients":["buyer@example.org"],"status":"failed","evidence_refs":["source.json"]}])
        result=self.stats([message("sent"),bounce])
        self.assertEqual(result["last_inbound_type"],"bounce")
        self.assertEqual(result["thread_id"],"thread-1")

    def test_quoted_cc_is_not_a_failed_recipient(self):
        bounce=message("bounce","relay@example.net","2026-09-22T12:00:00Z",kind="bounce",
            subject="Delivery has failed",to=["seller@example.com"],
            body="Delivery failed to invalid@example.org.\nOriginal Message\nCc: buyer@example.org",
            delivery_failures=[{"recipients":["invalid@example.org"],"status":"failed","evidence_refs":["source.json"]}])
        result=self.stats([message("sent"),bounce])
        self.assertIsNone(result["last_inbound_type"])
        self.assertTrue(result["ready"])

    def test_missing_failed_recipient_requires_review_and_delay_is_not_bounce(self):
        bounce=message("bounce","relay@example.net","2026-09-22T12:00:00Z",kind="bounce",to=["seller@example.com"])
        self.assertFalse(self.stats([message("sent"),bounce])["ready"])
        for status in (None,"delayed","unknown"):
            failure={"recipients":["buyer@example.org"],"evidence_refs":["source.json"]}
            if status is not None:failure["status"]=status
            bounce["delivery_failures"]=[failure]
            result=self.stats([message("sent"),bounce])
            self.assertEqual(result["last_inbound_type"],"unknown")
            self.assertIsNone(result["unanswered_count"])

    def test_calendar_subject_and_quoted_ooo_do_not_override_review(self):
        invite=message("invite","buyer@example.org","2026-09-22T12:00:00Z",kind="calendar",subject="Accepted: Review")
        self.assertFalse(self.stats([message("sent"),invite])["has_substantive_reply"])
        reply=message("reply","buyer@example.org","2026-09-23T12:00:00Z",kind="substantive",
            subject="Re: Automatic reply",body="Please send the agreement.\nOn Monday Seller wrote:\nOut of office")
        self.assertTrue(self.stats([message("sent"),invite,reply])["has_substantive_reply"])
        self.assertEqual(kind_of(message("prefix",subject="Accepted: Review")),"unknown")

    def test_dates_compare_instants_not_iso_strings(self):
        rows=[message("sent",date="2026-09-21T01:00:00+14:00"),
              message("reply","buyer@example.org","2026-09-20T12:00:00Z",kind="substantive")]
        self.assertEqual(self.stats(rows)["unanswered_count"],0)

    def test_unverified_counts_and_complete_empty_history(self):
        result=self.stats([message("sent")],complete=False,history_complete=False)
        self.assertIsNone(result["sent_count"])
        self.assertEqual(result["observed_sent_count"],1)
        self.assertIsNone(result["has_substantive_reply"])
        self.assertIsNone(result["unanswered_count"])
        empty=self.stats([])
        self.assertEqual(empty["sent_count"],0)
        self.assertEqual(empty["unanswered_count"],0)
        self.assertFalse(empty["has_substantive_reply"])

    def test_quote_and_signed_url_not_in_digest(self):
        text='<p>New https://example.org/file?secret=token</p><blockquote>Private old text</blockquote>'
        self.assertEqual(clean(text,300),"New https://example.org/file")
        self.assertEqual(clean("New\nOn Monday Someone wrote:\nold",300),"New")

    def test_duplicate_message_counts_once_and_conflicts_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"a.json",Path(tmp)/"b.json"
            doc={"result":{"email_results":{"emails":[message("same")]}}}
            a.write_text(json.dumps(doc));b.write_text(json.dumps(doc))
            self.assertEqual(len(load_messages([a,b])),1)
            doc["result"]["email_results"]["emails"][0]["subject"]="Changed"
            b.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):load_messages([a,b])

    def test_failed_source_and_malformed_rows_are_contextual(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"failed.json"
            for result in ({"error":"timeout"},{"email_results":{"emails":[None]}},
                           {"email_results":{"emails":[message("m",date="2026-09-20")]}},
                           {"email_results":{"emails":[message("m",sender=["buyer@example.org"])]}}):
                path.write_text(json.dumps({"result":result}))
                with self.assertRaisesRegex(ValueError,"failed.json"):load_messages([path])


class MailReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.calls=self.root/"calls";self.calls.mkdir()
        self.raw=self.root/"raw";self.raw.mkdir()
        self.since=datetime.fromisoformat("2026-09-23T09:00:00+00:00")

    def pair(self,name,rows,query_id="history",cursor=None,next_cursor=None,total=None,**selection):
        path=self.raw/f"{name}.json"
        source=[{k:v for k,v in row.items() if k not in {"classification","delivery_failures"}} for row in rows]
        path.write_text(json.dumps({"result":{"email_results":{"emails":source}}}))
        normalized=deepcopy(rows)
        for row in normalized:
            annotations=([row["classification"]] if "classification" in row else [])+row.get("delivery_failures",[])
            for annotation in annotations:annotation["evidence_refs"]=[f"../raw/{name}.json"]
        args={"query_id":query_id,"source":"mail","selection":"contact_history","owner_id":"owner-1",
            "provider_query":"Synthetic query","cursor":cursor,"addresses":["buyer@example.org"],
            "direction":"both","start_date":None,"end_date":None,**selection}
        response={"status":"success","records":normalized,"total_count":len(rows) if total is None else total,
            "next_cursor":next_cursor,"provider_reference":f"../raw/{name}.json"}
        (self.calls/f"input_{name}.json").write_text(json.dumps({"started_at":self.since.isoformat(),"arguments":args}))
        (self.calls/f"output_{name}.json").write_text(json.dumps({"completed_at":self.since.isoformat(),"result":response}))
        return path

    def result(self,paths,**kwargs):
        return load_mail_evidence(paths,self.calls,self.since,"owner-1",{"buyer@example.org"},**kwargs)

    def test_complete_empty_and_multipage_history(self):
        empty=self.pair("empty",[])
        self.assertTrue(self.result([empty])["ready"])
        for path in self.calls.iterdir():path.unlink()
        first=self.pair("first",[message("one")],next_cursor="page-2",total=2)
        second=self.pair("second",[message("two","buyer@example.org",kind="substantive")],cursor="page-2",total=2)
        result=self.result([first,second])
        self.assertTrue(result["ready"],result["errors"])
        self.assertEqual(len(result["messages"]),2)
        self.assertEqual(result["messages"][1]["classification"]["kind"],"substantive")

    def test_partial_history_and_missing_bound_cannot_prove_cold(self):
        path=self.pair("limited",[],start_date="2026-09-01")
        self.assertFalse(self.result([path])["ready"])
        self.assertTrue(self.result([path],require_all_history=False)["ready"])
        req=self.calls/"input_limited.json";doc=json.loads(req.read_text());del doc["arguments"]["start_date"];req.write_text(json.dumps(doc))
        self.assertFalse(self.result([path])["ready"])

    def test_bad_chains_and_explicit_terminal_required(self):
        path=self.pair("partial",[message("one")],next_cursor="missing",total=2)
        self.assertFalse(self.result([path])["ready"])
        out=self.calls/"output_partial.json";doc=json.loads(out.read_text());del doc["result"]["next_cursor"];out.write_text(json.dumps(doc))
        self.assertFalse(self.result([path])["ready"])

    def test_unrelated_complete_empty_query_cannot_bless_input(self):
        self.pair("complete",[])
        unrelated=self.raw/"unrelated.json";unrelated.write_text('{"result":{"email_results":{"emails":[]}}}')
        self.assertFalse(self.result([unrelated])["ready"])

    def test_missing_envelope_and_content_changes_fail(self):
        one=self.pair("one",[message("one")],next_cursor="p2",total=2)
        two=self.pair("two",[message("two")],cursor="p2",total=2)
        self.assertFalse(self.result([one])["ready"])
        doc=json.loads(two.read_text());doc["result"]["email_results"]["emails"][0]["subject"]="Changed";two.write_text(json.dumps(doc))
        self.assertFalse(self.result([one,two])["ready"])

    def test_overlapping_complete_queries_deduplicate_and_conflicts_fail(self):
        one=self.pair("one",[message("same",kind="substantive")],query_id="first")
        two=self.pair("two",[message("same",kind="substantive")],query_id="second")
        result=self.result([one,two]);self.assertTrue(result["ready"],result["errors"])
        self.assertEqual(len(result["messages"]),1)
        two=self.pair("two",[message("same",subject="Changed")],query_id="second")
        self.assertFalse(self.result([one,two])["ready"])

    def test_legacy_envelope_and_classification_without_source_fail_decisions(self):
        path=self.pair("one",[message("one")])
        self.assertEqual(len(load_messages([path])),1)
        self.assertFalse(load_mail_evidence([path])["ready"])
        out=self.calls/"output_one.json";doc=json.loads(out.read_text())
        doc["result"]["records"][0]["classification"]={"kind":"substantive","basis":"content_review","evidence_refs":["missing.json"]}
        out.write_text(json.dumps(doc))
        self.assertFalse(self.result([path])["ready"])

    def test_contact_scope_direction_narrowing_and_expired_end_fail(self):
        for selection in ({"addresses":["other@example.org"]},{"direction":"inbound"},
                          {"extra_filters":["subject filter"]},{"end_date":"2026-09-22"}):
            path=self.pair("one",[],**selection)
            self.assertFalse(self.result([path])["ready"])

    def test_finite_end_uses_configured_local_day(self):
        self.since=datetime.fromisoformat("2026-09-23T23:00:00+00:00")
        path=self.pair("one",[],end_date="2026-09-24")
        self.assertTrue(self.result([path],timezone_name="America/Los_Angeles")["ready"])
        self.assertFalse(self.result([path],timezone_name="Asia/Tokyo")["ready"])
