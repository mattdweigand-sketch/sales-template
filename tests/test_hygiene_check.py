"""Regression checks for next-step sentences, event timing, and linked activity."""
from __future__ import annotations
import datetime as dt
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import hygiene_check as hygiene
from zoneinfo import ZoneInfo


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


class HygieneAuditRegressions(unittest.TestCase):
    setUp = PipelineTimingTests.setUp
    event = PipelineTimingTests.event
    result = PipelineTimingTests.result

    def test_earliest_event_uses_instant_not_input_order(self):
        late = self.event("2026-09-21T16:00:00-07:00", "2026-09-21T17:00:00-07:00")
        early = self.event("2026-09-21T09:00:00-07:00", "2026-09-21T10:00:00-07:00")
        late["Id"], early["Id"] = "late", "early"
        for events in ([late, early], [early, late]):
            self.assertEqual(self.result(events)["upcoming_event_evidence"]["id"], "early")

    def test_date_only_candidate_does_not_get_an_invented_time(self):
        unknown = self.event(None, None)
        unknown["Id"] = "unknown"
        known = self.event("2026-09-21T09:00:00-07:00", "2026-09-21T10:00:00-07:00")
        result = self.result([known, unknown])
        self.assertTrue(result["upcoming_event_order_uncertain"])
        self.assertIn("order uncertain", hygiene.fmt(result))
        self.assertIsNone(next(e for e in result["unverified_events"] if e["id"] == "unknown")["start"])

    def test_zoneinfo_dates_and_local_midnight(self):
        self.policy["identity"] = {"timezone": "America/Los_Angeles"}
        spring = hygiene.resolve_as_of(self.policy, "2026-03-08")
        autumn = hygiene.resolve_as_of(self.policy, "2026-11-01")
        self.assertEqual(spring.isoformat(), "2026-03-08T00:00:00-08:00")
        self.assertEqual(autumn.isoformat(), "2026-11-01T00:00:00-07:00")
        instant = hygiene.resolve_as_of(self.policy, as_of="2026-11-02T07:30:00Z")
        self.assertEqual(instant.date(), dt.date(2026, 11, 1))
        with self.assertRaises(ValueError):
            hygiene.resolve_as_of(self.policy, "2026-11-02", "2026-11-02T07:30:00Z")

    def test_repeated_hour_orders_by_utc(self):
        self.as_of = dt.datetime.fromisoformat("2026-11-01T00:00:00-07:00")
        late = self.event("2026-11-01T01:15:00-08:00", "2026-11-01T01:45:00-08:00")
        early = self.event("2026-11-01T01:45:00-07:00", "2026-11-01T01:55:00-07:00")
        late["Id"], early["Id"] = "late", "early"
        self.assertEqual(self.result([late, early])["upcoming_event_evidence"]["id"], "early")
        zone = ZoneInfo("America/Los_Angeles")
        start = dt.datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
        end = dt.datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
        as_of = dt.datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0)
        self.assertEqual(hygiene.classify_event_timing(start, end, as_of), "in_progress")

    def test_blank_values_and_known_types_are_distinct(self):
        self.policy["pipeline"]["required_fields"] = {"S2": ["Amount", "Checkbox", "CustomText"]}
        self.opp.update(Amount=0, Checkbox=False, CustomText="  ")
        result = self.result([])
        self.assertEqual(result["blank_fields"], ["CustomText"])
        self.assertEqual(result["errors"], [])
        self.assertIn("Checkbox", result["unverified_field_types"])
        self.opp["Amount"] = False
        self.assertTrue(any("Amount must be number" in e for e in self.result([])["errors"]))
        for value in (None, "", "  ", [], {}):
            self.assertTrue(hygiene.is_blank(value))
        self.assertFalse(hygiene.is_blank(False))
        self.assertFalse(hygiene.is_blank(0))

    def test_declared_custom_type_is_applied_without_guessing(self):
        self.policy["pipeline"]["required_fields"] = {"S2": ["Checkbox"]}
        self.opp["Checkbox"] = "false"
        result = hygiene.evaluate([self.opp], [], [], self.policy, as_of=self.as_of, field_types={"Checkbox": "boolean"})
        self.assertFalse(result["ready"])
        self.assertTrue(any("Checkbox must be boolean" in e for e in result["errors"]))

    def test_bad_activity_preserves_other_record_diagnostics(self):
        self.opp["NextSteps"] = None
        bad = {"Id": "bad-task", "WhatId": "opp-1", "ActivityDate": "not-a-date", "IsClosed": True}
        other = {**self.opp, "Id": "opp-2", "AccountId": "account-2"}
        result = hygiene.evaluate([self.opp, other], [bad], [], self.policy, as_of=self.as_of)
        self.assertFalse(result["ready"])
        first, second = result["results"]
        self.assertNotIn("stale", first["triggers"])
        self.assertIsNone(first["task_gap"])
        self.assertIn("blank_field", first["triggers"])
        self.assertIn("stale", second["triggers"])
        self.assertTrue(any("bad-task" in error for error in result["errors"]))

    def test_unlinked_bad_activity_blocks_global_dependent_claims(self):
        self.opp["NextSteps"] = None
        result = hygiene.evaluate([self.opp], [None], [], self.policy, as_of=self.as_of)
        self.assertFalse(result["ready"])
        self.assertNotIn("stale", result["results"][0]["triggers"])
        self.assertIn("Task row 0", result["errors"][0])

    def test_completed_task_requires_activity_date_but_open_task_can_be_undated(self):
        self.opp["NextSteps"] = None
        for value in (None, ""):
            for state in ({"IsClosed": True}, {"Status": "Completed"}):
                with self.subTest(value=value, state=state):
                    task = {"Id": "undated", "WhatId": "opp-1", "ActivityDate": value, **state}
                    outcome = hygiene.evaluate([self.opp], [task], [], self.policy, as_of=self.as_of)
                    result = outcome["results"][0]
                    self.assertFalse(outcome["ready"])
                    self.assertFalse(result["activity_complete"])
                    self.assertNotIn("stale", result["triggers"])
                    self.assertNotIn("new_activity", result["triggers"])
                    self.assertIn("blank_field", result["triggers"])
                    self.assertTrue(any("ActivityDate" in e and "undated" in e for e in outcome["errors"]))
            open_task = {"Id": "undated-open", "WhatId": "opp-1", "ActivityDate": value, "IsClosed": False}
            outcome = hygiene.evaluate([self.opp], [open_task], [], self.policy, as_of=self.as_of)
            self.assertTrue(outcome["ready"])
            self.assertTrue(outcome["results"][0]["activity_complete"])

    def test_contradictory_task_completion_is_incomplete(self):
        task = {"Id": "contradiction", "WhatId": "opp-1", "ActivityDate": "2026-09-20", "IsClosed": False, "Status": "Completed"}
        outcome = hygiene.evaluate([self.opp], [task], [], self.policy, as_of=self.as_of)
        self.assertFalse(outcome["ready"])
        self.assertTrue(any("contradicts" in e for e in outcome["errors"]))

    def test_reversed_event_marks_affected_scope_incomplete(self):
        self.opp["NextSteps"] = None
        event = self.event("2026-09-21T16:00:00Z", "2026-09-21T09:00:00Z")
        other = {**self.opp, "Id": "opp-2", "AccountId": "account-2"}
        outcome = hygiene.evaluate([self.opp, other], [], [event], self.policy, as_of=self.as_of)
        first, second = outcome["results"]
        self.assertFalse(outcome["ready"])
        self.assertFalse(first["activity_complete"])
        self.assertNotIn("stale", first["triggers"])
        self.assertNotIn("new_activity", first["triggers"])
        self.assertIn("blank_field", first["triggers"])
        self.assertTrue(second["activity_complete"])
        self.assertIn("stale", second["triggers"])
        self.assertTrue(any("event-1" in e and "EndDateTime precedes StartDateTime" in e for e in outcome["errors"]))

    def test_event_duration_compares_instants_and_allows_equal_boundary(self):
        for start, end in (("2026-09-21T09:00:00Z", "2026-09-21T09:00:00Z"),
                           ("2026-11-01T01:45:00-07:00", "2026-11-01T01:15:00-08:00")):
            with self.subTest(start=start, end=end):
                outcome = hygiene.evaluate([self.opp], [], [self.event(start, end)], self.policy, as_of=self.as_of)
                self.assertTrue(outcome["ready"], outcome["errors"])
        outcome = hygiene.evaluate([self.opp], [], [self.event("2026-11-01T01:15:00-08:00", "2026-11-01T01:45:00-07:00")], self.policy, as_of=self.as_of)
        self.assertFalse(outcome["ready"])

    def test_bad_opportunities_are_contextual_not_tracebacks(self):
        for row in (None, 42, {**self.opp, "AccountId": []}, {**self.opp, "CloseDate": "bad"}):
            result = hygiene.evaluate([row], [], [], self.policy, as_of=self.as_of)
            self.assertFalse(result["ready"])
            self.assertTrue(result["errors"])

    def test_policy_errors_fail_explicitly(self):
        for key, value in (("stale_days", True), ("close_warning_days", -1), ("in_scope_stages", ["unknown"]), ("stage_order", ["S2", "S2"])):
            policy = {**self.policy, "pipeline": {**self.policy["pipeline"], key: value}}
            with self.assertRaises(ValueError):
                hygiene.evaluate([], [], [], policy, as_of=self.as_of)

    def test_cli_returns_nonzero_and_preserves_json_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, value in (("policy", self.policy), ("opps", [self.opp]), ("tasks", [None])):
                (root / (name + ".json")).write_text(json.dumps(value))
            proc = subprocess.run([sys.executable, str(Path(hygiene.__file__)), str(root / "opps.json"), "--tasks", str(root / "tasks.json"), "--policy", str(root / "policy.json"), "--as-of", self.as_of.isoformat(), "--json"], capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(proc.returncode, 1)
            self.assertTrue(json.loads(proc.stdout)[0]["errors"])
            self.assertNotIn("Traceback", proc.stderr)


class HistoryPreservationTests(unittest.TestCase):
    def setUp(self):
        self.first = "9/22/26 SELLER - Follow up on 9/24.\n"
        self.history = "\n9/20/26 SELLER - Buyer replied.  \n9/18/26 SELLER - Initial call.\n"
        self.before = self.first + self.history
        self.new = "9/23/26 SELLER - Send proposal by 9/25.\n"

    def test_exact_supported_constructions(self):
        cases = [
            (self.before, self.new + self.before, "prepend"),
            ("Next: Old action · Seller · 9/23/26\n" + self.history, self.new + self.history, "replace_legacy"),
            (self.before, self.first + "9/23/26 SELLER - Buyer confirmed scope.\n" + self.history, "insert_history"),
            (self.before, self.before, "unchanged"),
            (None, self.new, "prepend"),
        ]
        for before, after, operation in cases:
            self.assertEqual(hygiene.validate_next_steps_change(before, after, operation), [])

    def test_history_edits_and_reordering_are_rejected(self):
        for changed in (self.before.replace("  \n", "\n"), self.first, self.before.replace("replied", "signed"), self.history + self.first):
            self.assertTrue(hygiene.validate_next_steps_change(self.before, self.new + changed, "prepend"))

    def test_legacy_replacement_cannot_remove_dated_current_entry(self):
        self.assertTrue(hygiene.validate_next_steps_change(self.before, self.new + self.history, "replace_legacy"))

    def test_history_insertion_cannot_change_current_entry(self):
        self.assertTrue(hygiene.validate_next_steps_change(self.before, self.new + self.history, "insert_history"))

    def test_boundaries_invalid_dates_and_lossy_markup_rejected(self):
        self.assertTrue(hygiene.validate_next_steps_change(self.before, self.new.rstrip() + self.before, "prepend"))
        self.assertTrue(hygiene.validate_next_steps_change(self.before, "9/31/26 SELLER - Note.\n" + self.before, "prepend"))
        self.assertTrue(hygiene.validate_next_steps_change("<p>old</p>", self.new + "old", "prepend"))
        self.assertTrue(hygiene.validate_next_steps_change(self.before, self.before, "rewrite"))


if __name__ == "__main__":
    unittest.main()
