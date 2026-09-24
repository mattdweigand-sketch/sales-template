import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from triage_check import evaluate

ROOT = Path(__file__).resolve().parents[1]


class TriageCheckTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "_shared/policy.example.json").read_text())
        self.policy["identity"]["timezone"] = "America/Los_Angeles"
        self.task = {"task_id": "task-1", "mailbox": "seller@example.com", "thread_id": "thread-1",
                     "existing_draft": False, "mail_complete": True, "relationship": "cold",
                     "last_sent_at": "2026-09-18T12:00:00-07:00", "last_reply_at": None,
                     "held_meeting_at": None, "meeting_moved": False, "internal_prep": False,
                     "unanswered_count": 2, "recipient": "confirmed", "cooldown_until": None,
                     "channel": "email", "bodies_complete": True, "source_refs": ["raw/task.json", "raw/thread.json"]}
        self.now = "2026-09-23T12:00:00-07:00"

    def check(self, **changes):
        task = dict(self.task, **changes)
        return evaluate({"tasks": [task]}, self.policy, self.now)

    def test_hold_boundary_and_calendar_days(self):
        self.task["last_sent_at"] = "2026-09-18T12:00:00-07:00"  # Friday
        for when, group, date in (("2026-09-19T12:00:00-07:00", "hold", "2026-09-20"),
                                  ("2026-09-20T12:00:00-07:00", "draft", "2026-09-22"),
                                  ("2026-09-21T12:00:00-07:00", "draft", "2026-09-23")):
            with self.subTest(when=when):
                self.now = when
                decision = self.check()["tasks"][0]
                self.assertEqual((decision["group"], decision["proposed_date"]), (group, date))

    def test_timezone_date_not_utc_date(self):
        self.now = "2026-09-20T01:00:00Z"  # still Saturday locally
        decision = self.check()["tasks"][0]
        self.assertEqual(decision["group"], "hold")
        self.assertEqual(decision["proposed_date"], "2026-09-20")

    def test_recycle_precedes_timed_hold_but_not_incomplete_history(self):
        self.task["last_sent_at"] = "2026-09-23T10:00:00-07:00"
        self.assertEqual(self.check(unanswered_count=7)["tasks"][0]["group"], "recycle")
        self.assertEqual(self.check(unanswered_count=7, mail_complete=False)["tasks"][0]["group"], "hold")
        self.assertNotEqual(self.check(unanswered_count=9, relationship="active")["tasks"][0]["group"], "recycle")

    def test_existing_draft_prevents_duplicate(self):
        self.assertEqual(self.check(existing_draft=True, unanswered_count=9)["tasks"][0]["group"], "held_existing_draft")
        self.assertEqual(self.check(existing_draft=None)["tasks"][0]["group"], "hold")

    def test_confirmed_inbound_without_outbound_is_manual_not_unknown(self):
        changes = dict(relationship="active", last_sent_at=None, last_reply_at="2026-09-22T12:00:00-07:00")
        self.assertEqual(self.check(**changes)["tasks"][0]["group"], "manual")
        self.assertEqual(self.check(**dict(changes, mail_complete=None))["tasks"][0]["group"], "hold")

    def test_uncertainty_never_becomes_draft_or_cold(self):
        for changes in ({"relationship": "unknown"}, {"bodies_complete": None}, {"recipient": "unknown"},
                        {"thread_id": None}, {"last_sent_at": None}, {"meeting_moved": None}):
            with self.subTest(changes=changes):
                decision = self.check(**changes)["tasks"][0]
                self.assertEqual(decision["group"], "hold")
                self.assertIsNone(decision["proposed_date"])

    def test_known_manual_task_does_not_require_unrelated_mail(self):
        self.assertEqual(self.check(internal_prep=True, mail_complete=False)["tasks"][0]["group"], "manual")

    def test_multiple_timed_holds_and_unknown_expiry(self):
        self.task["last_sent_at"] = "2026-09-23T10:00:00-07:00"
        out = self.check(cooldown_until="2026-10-10")["tasks"][0]
        self.assertEqual(out["proposed_date"], "2026-10-10")
        self.assertIsNone(self.check(cooldown_until="2026-10-10", recipient="unconfirmed")["tasks"][0]["proposed_date"])

    def test_draft_payloads_share_only_exact_proposal(self):
        draft = {"to": ["buyer@example.net"], "cc": [], "bcc": [], "subject": "Follow up", "body": "The same ask.", "attachments": []}
        self.task["draft"] = draft
        other = copy.deepcopy(self.task)
        other["task_id"] = "task-2"
        out = evaluate({"tasks": [self.task, other]}, self.policy, self.now)
        self.assertEqual(out["tasks"][0]["shared_draft_task_ids"], ["task-1", "task-2"])
        other["draft"]["to"] = ["someone-else@example.net"]
        out = evaluate({"tasks": [self.task, other]}, self.policy, self.now)
        self.assertTrue(out["errors"])
        self.assertEqual([d["group"] for d in out["tasks"]], ["hold", "hold"])
        other["thread_id"] = "different-thread"
        self.assertFalse(evaluate({"tasks": [self.task, other]}, self.policy, self.now)["errors"])

    def test_no_contact_field_needed_and_unverified_meeting_not_inferred(self):
        self.assertEqual(self.check()["tasks"][0]["group"], "draft")
        # Only confirmed held meetings enter this field; scheduled events remain null.
        self.assertNotEqual(self.check(held_meeting_at=None)["tasks"][0]["group"], "manual")
        self.assertTrue(self.check(held_meeting_at="2026-09-24T12:00:00-07:00")["errors"])

    def test_malformed_inputs_return_contextual_errors(self):
        for changes in ({"last_sent_at": "2026-09-01"}, {"unanswered_count": True},
                        {"existing_draft": "false"}, {"cooldown_until": "bad"}, {"source_refs": []}):
            with self.subTest(changes=changes):
                out = self.check(**changes)
                self.assertFalse(out["complete"])
                self.assertIn("tasks[0]", out["errors"][0])
        self.assertTrue(evaluate({"tasks": [None]}, self.policy, self.now)["errors"])
        self.assertTrue(evaluate({"tasks": [self.task, self.task]}, self.policy, self.now)["errors"])


if __name__ == "__main__":
    unittest.main()
