"""Regression checks for next-step sentences, event timing, and linked activity."""
from __future__ import annotations
import datetime as dt
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import hygiene_check as hygiene


class PipelineTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.as_of = dt.datetime.fromisoformat("2026-09-21T07:00:31-07:00")
        self.policy = {
            "pipeline": {
                "in_scope_stages": ["S2"], "stage_order": ["S0","S1","S2","S3","S4","S5"], "close_warning_before_stage": "S3", "required_fields": {}, "conditional_fields": [],
                "close_warning_days": 14, "stale_days": 14,
            }
        }
        self.opp = {
            "Id": "opp-1", "AccountId": "account-1", "StageName": "S2 - Solutioning",
            "CloseDate": "2026-12-31",
            "NextSteps": "Next: Discuss evaluation · the seller · 9/21/26\n9/19/26 SELLER - Call scheduled.",
        }

    def event(self, start: str | None, end: str | None) -> dict:
        return {
            "Id": "event-1", "AccountId": "account-1", "WhatId": "account-1",
            "ActivityDate": "2026-09-21", "StartDateTime": start, "EndDateTime": end,
            "Subject": "Search discussion",
        }

    def result(self, events: list, tasks: list | None = None) -> dict:
        acts = hygiene.index_activity(tasks or [], events, self.as_of.tzinfo)
        return hygiene.check(self.opp, self.policy, acts, self.as_of.date(), self.as_of)

    def test_afternoon_later_today_is_upcoming_not_new_activity(self) -> None:
        result = self.result([self.event("2026-09-21T21:00:00Z", "2026-09-21T21:45:00Z")])
        self.assertNotIn("new_activity", result["triggers"])
        self.assertIsNone(result["last_activity"])
        self.assertEqual(result["upcoming_event_evidence"]["timing"], "upcoming")

    def test_later_later_today_is_upcoming_not_new_activity(self) -> None:
        result = self.result([self.event("2026-09-21T18:00:00Z", "2026-09-21T18:30:00Z")])
        self.assertNotIn("new_activity", result["triggers"])

    def test_ongoing_meeting_is_not_completed(self) -> None:
        result = self.result([self.event("2026-09-21T13:50:00Z", "2026-09-21T14:30:00Z")])
        self.assertNotIn("new_activity", result["triggers"])
        self.assertEqual(result["upcoming_event_evidence"]["timing"], "in_progress")

    def test_ended_event_is_elapsed_not_proof_of_attendance(self) -> None:
        result = self.result([self.event("2026-09-21T12:00:00Z", "2026-09-21T12:30:00Z")])
        self.assertIn("new_activity", result["triggers"])
        self.assertEqual(result["new_activity_evidence"]["timing"], "elapsed")
        self.assertEqual(result["unverified_events"][0]["id"], "event-1")
        self.assertIn("attendance unverified", hygiene.fmt(result))

    def test_event_ending_at_cutoff_is_elapsed(self) -> None:
        result = self.result([self.event("2026-09-21T13:00:00Z", "2026-09-21T14:00:31Z")])
        self.assertIn("new_activity", result["triggers"])

    def test_date_only_today_is_not_held(self) -> None:
        result = self.result([self.event(None, None)])
        self.assertNotIn("new_activity", result["triggers"])
        self.assertEqual(result["unverified_events"][0]["timing"], "timing_unknown")

    def test_date_only_past_is_not_proof_of_completion(self) -> None:
        event = self.event(None, None)
        event["ActivityDate"] = "2026-09-20"
        self.assertNotIn("new_activity", self.result([event])["triggers"])

    def test_missing_end_after_start_requires_verification(self) -> None:
        result = self.result([self.event("2026-09-21T13:00:00Z", None)])
        self.assertNotIn("new_activity", result["triggers"])

    def test_end_before_start_requires_verification(self) -> None:
        result = self.result([self.event("2026-09-21T13:00:00Z", "2026-09-21T12:00:00Z")])
        self.assertNotIn("new_activity", result["triggers"])

    def test_naive_datetime_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            hygiene.parse_activity_timestamp("2026-09-21T07:00:00")

    def test_utc_midnight_uses_run_local_date(self) -> None:
        result = self.result([self.event("2026-09-21T01:00:00Z", "2026-09-21T01:30:00Z")])
        self.assertEqual(result["new_activity_evidence"]["date"], "2026-09-20")

    def test_account_linked_inbound_is_last_touch_and_deduplicated(self) -> None:
        task = {
            "Id": "inbound-1", "WhatId": "account-1", "AccountId": "account-1",
            "ActivityDate": "2026-09-21", "IsClosed": True,
            "Direction": "inbound", "Subject": "Credential request", "Who": {"Name": "Buyer"},
        }
        result = self.result([], [task])
        self.assertIn("new_activity", result["triggers"])
        self.assertEqual(result["last_activity_evidence"]["id"], "inbound-1")
        self.assertEqual(result["last_activity_evidence"]["contact"], "Buyer")
        self.assertEqual(result["new_activity_evidence"]["what_id"], "account-1")

    def test_open_inbound_task_is_not_a_completed_touch(self) -> None:
        task = {
            "Id": "task-1", "WhatId": "opp-1", "ActivityDate": "2026-09-21",
            "IsClosed": False, "Direction": "inbound", "Subject": "Inbound",
        }
        self.assertNotIn("new_activity", self.result([], [task])["triggers"])

    def test_outbound_is_last_touch_but_not_new_buyer_activity(self) -> None:
        task = {
            "Id": "task-1", "WhatId": "opp-1", "ActivityDate": "2026-09-21",
            "IsClosed": True, "Direction": "outbound", "Subject": "Sent",
        }
        result = self.result([], [task])
        self.assertNotIn("new_activity", result["triggers"])
        self.assertEqual(result["last_activity_evidence"]["id"], "task-1")

    def test_upcoming_event_clears_stale_without_becoming_a_touch(self) -> None:
        self.opp["NextSteps"] = None
        result = self.result([self.event("2026-09-21T18:00:00Z", "2026-09-21T18:30:00Z")])
        self.assertNotIn("stale", result["triggers"])
        self.assertIsNone(result["last_activity"])

    def test_unchanged_future_action_is_not_overdue(self) -> None:
        self.assertNotIn("next_passed", self.result([])["triggers"])


class DatedNextStepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.as_of = dt.datetime.fromisoformat("2026-09-22T15:28:00-07:00")
        self.policy = {
            "pipeline": {
                "in_scope_stages": ["S2"], "stage_order": ["S0","S1","S2","S3","S4","S5"], "close_warning_before_stage": "S3", "required_fields": {}, "conditional_fields": [],
                "close_warning_days": 14, "stale_days": 14,
            }
        }

    def check_text(self, text: str | None, tasks: list | None = None) -> dict:
        opportunity = {
            "Id": "opp-1", "AccountId": "account-1", "StageName": "S2 - Solutioning",
            "CloseDate": "2026-12-31", "NextSteps": text,
        }
        activity = hygiene.index_activity(tasks or [], [], self.as_of.tzinfo)
        return hygiene.check(
            opportunity, self.policy, activity, self.as_of.date(), self.as_of
        )

    def test_approved_sentence_uses_action_date_not_entry_date(self) -> None:
        text = (
            "9/22/26 SELLER - Follow up with Andrew on 9/24 for order form feedback, "
            "an admin introduction, signer, and decision date."
        )
        result = self.check_text(text)
        self.assertEqual(result["next"], "OK")
        self.assertEqual(result["next_format"], "dated_sentence")
        self.assertEqual(result["next_date"], "2026-09-24")
        self.assertEqual(result["newest_note"], "2026-09-22")
        self.assertEqual(result["next_action"], text.split(" SELLER - ", 1)[1])
        self.assertIsNone(result["next_owner"])
        self.assertNotIn("next_passed", result["triggers"])
        self.assertNotIn("stale", result["triggers"])
        self.assertNotIn("blank_field", result["triggers"])
        self.assertTrue(result["task_gap"])
        self.assertIn("OK 2026-09-24 (Follow up", hygiene.fmt(result))

    def test_full_year_and_by_are_supported(self) -> None:
        result = self.check_text("9/22/26 SELLER - Send the agreement by 9/25/2026.")
        self.assertEqual(result["next_date"], "2026-09-25")

    def test_overdue_sentence_preserves_due_date_check(self) -> None:
        result = self.check_text("9/22/26 SELLER - Follow up with Andrew by 9/21.")
        self.assertEqual(result["next_passed_days"], 1)
        self.assertIn("next_passed", result["triggers"])
        self.assertFalse(result["task_gap"])

    def test_old_written_date_with_future_deadline_is_not_overdue(self) -> None:
        result = self.check_text("9/10/26 SELLER - Send the agreement on 9/24.")
        self.assertNotIn("next_passed", result["triggers"])

    def test_cross_year_deadline_uses_explicit_year(self) -> None:
        result = self.check_text("12/30/26 SELLER - Send the agreement by 1/2/27.")
        self.assertEqual(result["next_date"], "2027-01-02")

    def test_yearless_deadline_uses_written_year_not_run_year(self) -> None:
        result = self.check_text("12/30/25 SELLER - Send the agreement by 12/31.")
        self.assertEqual(result["next_date"], "2025-12-31")

    def test_missing_deadline_never_uses_written_date(self) -> None:
        result = self.check_text("9/22/26 SELLER - Follow up with Andrew.")
        self.assertEqual(result["next"], "REVIEW")
        self.assertNotIn("next_date", result)
        self.assertIn("blank_field", result["triggers"])
        self.assertFalse(result["task_gap"])
        self.assertIn("No explicit on/by", hygiene.fmt(result))

    def test_multiple_possible_deadlines_require_review(self) -> None:
        result = self.check_text(
            "9/22/26 SELLER - Send the agreement on 9/24 after the email on 9/21."
        )
        self.assertEqual(result["next"], "REVIEW")
        self.assertNotIn("next_date", result)
        self.assertNotIn("next_passed", result["triggers"])
        self.assertFalse(result["task_gap"])

    def test_invalid_due_date_requires_review_without_crashing(self) -> None:
        result = self.check_text("9/22/26 SELLER - Send the agreement on 9/31.")
        self.assertEqual(result["next"], "REVIEW")
        self.assertIn("Invalid action due date", result["next_review_reason"])

    def test_invalid_written_date_requires_review_without_crashing(self) -> None:
        result = self.check_text("9/31/26 SELLER - Send the agreement on 10/1.")
        self.assertEqual(result["next"], "REVIEW")
        self.assertIsNone(result["newest_note"])

    def test_invalid_legacy_date_requires_review_without_crashing(self) -> None:
        result = self.check_text("Next: Send agreement · the seller · 9/31/26")
        self.assertEqual(result["next"], "REVIEW")

    def test_existing_legacy_format_still_works(self) -> None:
        result = self.check_text(
            "Next: Send agreement · the seller · 9/24/26\n9/20/26 SELLER - Buyer replied."
        )
        self.assertEqual(result["next"], "OK")
        self.assertEqual(result["next_format"], "legacy")
        self.assertEqual(result["next_owner"], "the seller")
        self.assertEqual(result["next_date"], "2026-09-24")
        self.assertNotIn("blank_field", result["triggers"])

    def test_legacy_duplicate_detection_is_preserved(self) -> None:
        result = self.check_text(
            "Next: Send agreement · the seller · 9/24/26\n"
            "Next: Send old agreement · the seller · 9/21/26"
        )
        self.assertEqual(result["duplicate_next_lines"], 2)
        self.assertIn("blank_field", result["triggers"])

    def test_historical_action_entries_do_not_override_current_deadline(self) -> None:
        result = self.check_text(
            "9/22/26 SELLER - Send the agreement on 9/24.\n"
            "9/21/26 SELLER - Follow up with Andrew on 9/21.\n"
            "9/18/26 SELLER - Buyer replied on 9/17."
        )
        self.assertEqual(result["next_date"], "2026-09-24")
        self.assertNotIn("duplicate_next_lines", result)
        self.assertNotIn("next_passed", result["triggers"])

    def test_task_gap_matches_action_date_not_entry_date(self) -> None:
        text = "9/22/26 SELLER - Follow up with Andrew on 9/24."
        task = {
            "Id": "task-1", "WhatId": "opp-1", "ActivityDate": "2026-09-22",
            "IsClosed": False, "Subject": "Follow up with Andrew",
        }
        self.assertTrue(self.check_text(text, [task])["task_gap"])
        task["ActivityDate"] = "2026-09-24"
        self.assertFalse(self.check_text(text, [task])["task_gap"])

    def test_empty_and_undated_entries_remain_missing(self) -> None:
        for text in (None, "", "Follow up with Andrew on 9/24."):
            with self.subTest(text=text):
                self.assertEqual(self.check_text(text)["next"], "MISSING")

    def test_html_paragraphs_keep_history_on_separate_lines(self) -> None:
        result = self.check_text(
            "<p>9/22/26 SELLER - Follow up with Andrew on 9/24.</p>"
            "<p>9/20/26 SELLER - Buyer replied.</p>"
        )
        self.assertEqual(result["next"], "OK")
        self.assertEqual(result["next_date"], "2026-09-24")


if __name__ == "__main__":
    unittest.main()
