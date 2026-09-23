"""Behavioral checks for contact evidence and thread digests using synthetic mail."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gmail_contact_stats import contact_stats
from gmail_thread_digest import clean
from mail_evidence import load_messages


def message(key, sender="seller@example.com", date="2026-09-20T12:00:00Z", **extra):
    return {"email_id":key, "thread_id":"thread-1", "date":date, "from_":sender,
            "to":["buyer@example.org"], "subject":"An evaluation", **extra}


class MailTests(unittest.TestCase):
    def stats(self, rows):
        return contact_stats(rows, "seller@example.com", ["example.com"], {"buyer@example.org"})[0]

    def test_reply_resets_unanswered_but_ooo_does_not(self):
        rows = [message("sent-1"), message("reply", "buyer@example.org", "2026-09-21T12:00:00Z"),
                message("sent-2", date="2026-09-22T12:00:00Z"),
                message("ooo", "buyer@example.org", "2026-09-23T12:00:00Z", subject="Automatic reply")]
        result = self.stats(rows)
        self.assertEqual(result["unanswered_count"], 1)
        self.assertTrue(result["has_substantive_reply"])
        self.assertEqual(result["last_inbound_type"], "ooo")

    def test_relay_bounce_is_attributed_without_using_bounce_thread(self):
        rows = [message("sent"), message("bounce", "relay@example.net", "2026-09-22T12:00:00Z",
                subject="Delivery has failed", body="Failed for buyer@example.org", thread_id="bounce-thread")]
        result = self.stats(rows)
        self.assertEqual(result["last_inbound_type"], "bounce")
        self.assertEqual(result["thread_id"], "thread-1")

    def test_calendar_and_quoted_ooo_are_not_false_replies(self):
        rows = [message("sent"), message("invite", "buyer@example.org", "2026-09-22T12:00:00Z", subject="Accepted: Review")]
        self.assertFalse(self.stats(rows)["has_substantive_reply"])
        rows.append(message("reply", "buyer@example.org", "2026-09-23T12:00:00Z",
                    body="Please send the agreement.\nOn Monday Seller wrote:\nOut of office"))
        self.assertTrue(self.stats(rows)["has_substantive_reply"])

    def test_dates_compare_instants_not_iso_strings(self):
        rows = [message("sent", date="2026-09-21T01:00:00+14:00"),
                message("reply", "buyer@example.org", "2026-09-20T12:00:00Z")]
        self.assertEqual(self.stats(rows)["unanswered_count"], 0)

    def test_quote_and_signed_url_not_in_digest(self):
        text = '<p>New https://example.org/file?secret=token</p><blockquote>Private old text</blockquote>'
        self.assertEqual(clean(text, 300), "New https://example.org/file")
        self.assertEqual(clean("New\nOn Monday Someone wrote:\nold",300), "New")

    def test_duplicate_message_counts_once_and_conflicts_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a.json", Path(tmp)/"b.json"
            doc = {"result":{"email_results":{"emails":[message("same")]}}}
            a.write_text(json.dumps(doc)); b.write_text(json.dumps(doc))
            self.assertEqual(len(load_messages([a,b])), 1)
            doc["result"]["email_results"]["emails"][0]["subject"] = "Changed"
            b.write_text(json.dumps(doc))
            with self.assertRaises(ValueError): load_messages([a,b])

    def test_failed_source_is_not_empty_inbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"failed.json"
            path.write_text('{"result":{"error":"timeout"}}')
            with self.assertRaises(ValueError): load_messages([path])
