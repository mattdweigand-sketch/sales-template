"""Synthetic regressions for review isolation, invalidation and exact result accounting."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import runs
import wrappers
import check_repo


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "output", "__pycache__"))
        for example in (self.root / "_shared").glob("*.example.*"):
            shutil.copyfile(example, example.with_name(example.name.replace(".example", "")))
        self.command = next(iter(wrappers.load_routes(self.root)))
        self.path = runs.init(self.root, "synthetic-001", self.command)

    def ready(self):
        (self.path / "call.txt").write_text("Synthetic selected call, no provider invoked.")
        (self.path / "selected.json").write_text(json.dumps({"call_id": "synthetic-call", "source_refs": ["call.txt"]}))
        staged = self.path / "proposed-policy.json"
        staged.write_bytes((self.root / "_shared/policy.json").read_bytes())
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        self.inputs = {"started_at": "2026-09-23T09:00:00Z", "mode": None,
                       "sources": {"selected_call": "selected.json"}, "unavailable_sources": [],
                       "effects": [{"id":"A1", "operation":"local_config", "destination":"_shared/policy.json",
                                    "record_id":None, "preimage":{"sha256":digest}, "payload":{"staged_file":"proposed-policy.json"},
                                    "source_refs":["proposed-policy.json"]}]}
        (self.path / "inputs.json").write_text(json.dumps(self.inputs))
        after = {"A1": {"_shared/policy.json": digest}}
        (self.path / "01_review.md").write_text("---\nstatus: ready\nexpected_after: " + json.dumps(after) + "\n---\n\n# Synthetic review\n\nSelected call source is call.txt. No gaps were found.\n\n## Effect A1\nInspect exact staged synthetic configuration in inputs.json.\n")

    def approve(self):
        return runs.record_review(self.root, self.path.name, "Synthetic reviewer", "test-only-approval", ["A1"])

    def result(self, review, effects=None):
        if effects is None:
            effects = [{"id": "A1", "status": "verified", "provider_reference": "synthetic-provider-1", "readback_reference": "synthetic-readback-1"}]
        (self.path / "02_result.json").write_text(json.dumps({"recorded_at": "2026-01-11T00:00:00Z", "summary": "Synthetic result; no service called", "review_snapshot": review["snapshot"], "effects": effects}))

    def test_starter_never_counts_as_ready(self):
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "draft")

    def save_inputs(self):
        (self.path / "inputs.json").write_text(json.dumps(self.inputs))

    def bind_workflow(self, name, mode=None):
        self.ready()
        (self.path / "request.md").write_text(f"---\nrun_id: {self.path.name}\nworkflow: {name}\n---\nSynthetic request.\n")
        (self.path / "01_review.md").write_text("---\nstatus: ready\n---\n# Synthetic report\nComplete synthetic census reviewed; evidence is retained in bound sources.\n")
        self.inputs.update(mode=mode, sources={}, effects=[])
        (self.path / "calls").mkdir()
        (self.path / "raw").mkdir()
        self.inputs["sources"]["calls"] = "calls"

    def pair(self, name, source, records, selection, **extra):
        arguments = {"query_id":name, "source":source, "selection":selection, "owner_id":"seller-record", "provider_query":"Synthetic query", "cursor":None, **extra}
        raw = {"result":{"email_results":{"emails":records}}} if source == "mail" else {"records":records}
        (self.path / "raw" / (name + ".json")).write_text(json.dumps(raw))
        result = {"status":"success", "records":records, "total_count":len(records), "next_cursor":None, "provider_reference":"../raw/" + name + ".json"}
        for prefix, data in (("input", {"started_at":self.inputs["started_at"],"arguments":arguments}), ("output", {"completed_at":self.inputs["started_at"],"result":result})):
            (self.path / "calls" / (prefix + "_" + name + ".json")).write_text(json.dumps(data))

    def bind_rows(self, key, records):
        filename = key + ".json"
        (self.path / filename).write_text(json.dumps(records))
        self.inputs["sources"][key] = filename

    def revenue_fixture(self, name="pipeline-review"):
        self.bind_workflow(name, "extended" if name == "pipeline-review" else None)
        opp = {"Id":"o1", "OwnerId":"seller-record", "IsClosed":False, "AccountId":"a1", "Account":{"Name":"Synthetic Buyer"}, "StageName":"S2", "CloseDate":"2026-09-30", "Amount":100, "LeadSource":"Website", "CustomerPointOfContact":"Alex", "NextSteps":"9/23/26 SELLER - Ask Alex for feedback by 9/24/26."}
        self.bind_rows("opportunities", [opp]); self.bind_rows("tasks", []); self.bind_rows("events", [])
        self.pair("opps", "crm", [opp], "all_owned_open", object="Opportunity")
        for obj, records in (("Contact", [{"Id":"c1", "AccountId":"a1", "Email":"buyer@example.org"}]), ("Task", []), ("Event", [])):
            self.pair(obj, "crm", records, "linked_accounts_and_opportunities", object=obj, account_ids=["a1"], opportunity_ids=["o1"], fields=["StartDateTime","EndDateTime"])
        self.pair("mail", "mail", [], "account_inbound", domains=["example.org"], start_date="2026-07-01", end_date=None)
        self.pair("calendar", "calendar", [], "account_calendar", account_ids=["a1"], start_date="2026-08-01", end_date="2026-11-01")
        if name == "forecast-weekly":
            self.pair("booked", "crm", [], "booked_in_quarter", object="Opportunity", start_date="2026-07-01", end_date="2026-10-01")
            self.bind_rows("forecast", {"quarter_start":"2026-07-01", "quarter_end":"2026-10-01", "target":None,
                "rows":[{"deal_id":"o1", "population":"current", "bucket":"upside", "amount":"100", "currency":"USD", "revenue_basis":"synthetic basis", "source_refs":["raw/opps.json"]}]})
        self.save_inputs()

    def test_pipeline_recomputes_coverage_and_exact_census(self):
        self.revenue_fixture()
        checked = runs.validate(self.root, self.path.name)
        self.assertTrue(checked["report_complete"], checked["errors"])
        self.bind_rows("opportunities", []); self.save_inputs()
        checked = runs.validate(self.root, self.path.name)
        self.assertFalse(checked["report_complete"])
        self.assertTrue(any("census" in e for e in checked["errors"]), checked["errors"])

    def test_forecast_recomputes_population_amount_and_target(self):
        self.revenue_fixture("forecast-weekly")
        checked = runs.validate(self.root, self.path.name)
        self.assertTrue(checked["report_complete"], checked["errors"])
        source = self.path / "forecast.json"
        original = source.read_text()
        for field, value in (("amount", "80"), ("population", "booked")):
            doc = json.loads(original); doc["rows"][0][field] = value; source.write_text(json.dumps(doc))
            self.assertFalse(runs.validate(self.root, self.path.name)["report_complete"])
        doc = json.loads(original); doc["rows"] = []; source.write_text(json.dumps(doc))
        self.assertFalse(runs.validate(self.root, self.path.name)["report_complete"])
        doc = json.loads(original); doc["target"] = "999"; source.write_text(json.dumps(doc))
        self.assertFalse(runs.validate(self.root, self.path.name)["report_complete"])

    def test_consumed_forecast_configuration_is_validated(self):
        self.revenue_fixture("forecast-weekly")
        target = self.root / "_shared/policy.json"
        original = target.read_text()
        for section, key, value in (("reporting", "amount_decimal_places", True), ("forecast", "sources", ["fax"]), ("forecast", "commit_stages", ["UNCONFIGURED"]), ("forecast", "activity_days", -1), ("forecast", "target_default", True)):
            doc = json.loads(original); doc[section][key] = value; target.write_text(json.dumps(doc))
            checked = runs.validate(self.root, self.path.name)
            self.assertFalse(checked["report_complete"], (section,key,checked))

    def test_shared_review_input_ancestor_symlink_rejected(self):
        self.ready()
        (self.root / "_shared/linked-dir").symlink_to(self.path, target_is_directory=True)
        target = self.root / "_shared/policy.json"
        policy = json.loads(target.read_text()); policy["review_inputs"].append("_shared/linked-dir/call.txt")
        target.write_text(json.dumps(policy))
        self.assertFalse(runs.validate(self.root, self.path.name)["can_review"])

    def test_triage_recomputes_thread_facts_and_census(self):
        self.bind_workflow("task-triage-speed-run")
        tasks = [{"Id":"t1", "ActivityDate":"2026-09-23", "Status":"Open"}]
        self.bind_rows("tasks", tasks)
        self.pair("tasks", "crm", tasks, "selected_tasks", object="Task", task_ids=["t1"])
        message = {"email_id":"m1", "thread_id":"th1", "date":"2026-09-19T12:00:00Z", "from_":"seller@example.com", "to":["buyer@example.org"], "cc":[], "subject":"Synthetic follow-up", "body_text":"A synthetic prior question."}
        self.pair("history", "mail", [message], "contact_history", addresses=["buyer@example.org"], direction="both", start_date=None, end_date=None)
        self.inputs["sources"]["mail"] = "raw/history.json"
        task = {"task_id":"t1", "mailbox":"seller@example.com", "thread_id":"th1", "existing_draft":False, "mail_complete":True, "relationship":"cold", "last_sent_at":message["date"], "last_reply_at":None, "held_meeting_at":None, "meeting_moved":False, "internal_prep":False, "unanswered_count":1, "recipient":"confirmed", "cooldown_until":None, "channel":"email", "bodies_complete":True, "source_refs":["raw/history.json", "raw/tasks.json"]}
        self.bind_rows("triage", {"tasks":[task]}); self.save_inputs()
        checked = runs.validate(self.root, self.path.name)
        self.assertTrue(checked["report_complete"], checked["errors"])
        task["unanswered_count"] = 7
        self.bind_rows("triage", {"tasks":[task]})
        checked = runs.validate(self.root, self.path.name)
        self.assertFalse(checked["report_complete"])
        self.assertTrue(any("unanswered_count" in e for e in checked["errors"]), checked["errors"])
        task["unanswered_count"] = 1
        task["draft"] = {"to":["buyer@example.org"], "cc":[], "bcc":[], "subject":"Synthetic follow-up", "body":"Reviewed question.", "attachments":[]}
        effect = {"id":"A1", "operation":"draft", "destination":"mail", "record_id":None,
                  "preimage":{"existing_draft_ids":[]}, "payload":{**task["draft"], "thread_id":"th1", "reply_to_message_id":"m1"}, "source_refs":["raw/history.json"]}
        self.inputs["effects"] = [effect]
        with (self.path / "01_review.md").open("a") as stream: stream.write("\n## Effect A1\nSee exact inputs payload.\n")
        self.bind_rows("triage", {"tasks":[task]}); self.save_inputs()
        self.assertTrue(runs.validate(self.root, self.path.name)["ready_for_effects"])
        effect["payload"]["body"] = "Different proposal"
        self.save_inputs()
        self.assertFalse(runs.validate(self.root, self.path.name)["ready_for_effects"])
        effect["payload"]["body"] = task["draft"]["body"]
        effect["payload"]["to"] = ["unrelated@example.net"]
        self.save_inputs()
        self.assertFalse(runs.validate(self.root, self.path.name)["ready_for_effects"])
        effect["payload"]["to"] = task["draft"]["to"]; self.save_inputs()
        message["body_text"] = None
        self.pair("history", "mail", [message], "contact_history", addresses=["buyer@example.org"], direction="both", start_date=None, end_date=None)
        self.assertFalse(runs.validate(self.root, self.path.name)["ready_for_effects"])
        message["body_text"] = "Synthetic outbound"
        other_reply = {**message, "email_id":"m2", "thread_id":"other-thread", "date":"2026-09-18T12:00:00Z", "from_":"buyer@example.org", "to":["seller@example.com"],
                       "classification":{"kind":"substantive", "basis":"content_review", "evidence_refs":["../raw/history.json"]}}
        self.pair("history", "mail", [message, other_reply], "contact_history", addresses=["buyer@example.org"], direction="both", start_date=None, end_date=None)
        checked = runs.validate(self.root, self.path.name)
        self.assertFalse(checked["ready_for_effects"])
        self.assertTrue(any("cold relationship" in e for e in checked["errors"]), checked["errors"])

    def test_workflow_effect_fields_match_permitted_operations(self):
        self.ready()
        cases = [("interaction-sync", "Task", "create", {"TaskSubtype":"Call", "Status":"Completed"}),
                 ("interaction-sync", "OpportunityContactRole", "create", {"OpportunityId":"o1", "ContactId":"c1", "Role":"Evaluator"}),
                 ("interaction-sync", "Opportunity", "update", {"LeadSource":"Website", "CustomerPointOfContact":"Alex"}),
                 ("pipeline-review", "Task", "create", {"Status":"Not Started"}),
                 ("task-triage-speed-run", "Contact", "update", {"Title":"Manager", "Description":"New note.\nOld"}),
                 ("task-triage-speed-run", "Task", "update", {"Subject":"Follow up with Alex"})]
        for name, destination, operation, payload in cases:
            effect = {"id":"A1", "operation":operation, "destination":destination, "record_id":None if operation == "create" else "r1",
                      "preimage":{k:"Old" if k == "Description" else None for k in payload}, "payload":payload, "source_refs":["call.txt"]}
            self.assertEqual(runs.check_effects(self.path, name, {"effects":[effect]}, ["A1"]), [], (name,payload))
            effect["operation"] = "update"; effect["record_id"] = "r1"; effect["payload"] = {"OwnerId":"different-owner"}; effect["preimage"] = {"OwnerId":"old-owner"}
            self.assertTrue(runs.check_effects(self.path, name, {"effects":[effect]}, ["A1"]))

    def test_known_effect_field_types_are_checked(self):
        self.ready()
        for destination, payload in (("Opportunity", {"Amount":True}), ("Task", {"ActivityDate":"bad-date"})):
            effect = {"id":"A1", "operation":"update", "destination":destination, "record_id":"r1", "preimage":{k:None for k in payload}, "payload":payload, "source_refs":["call.txt"]}
            self.assertTrue(runs.check_effects(self.path, "interaction-sync", {"effects":[effect]}, ["A1"]))
        draft = {"to":["buyer@example.org"], "cc":[], "bcc":[], "subject":"Subject", "body":"Body", "attachments":[], "thread_id":None, "reply_to_message_id":None}
        for key, value in (("to", [None]), ("thread_id", {}), ("reply_to_message_id", [])):
            effect = {"id":"A1", "operation":"draft", "destination":"mail", "record_id":None, "preimage":{"existing_draft_ids":[]}, "payload":{**draft, key:value}, "source_refs":["call.txt"]}
            self.assertTrue(runs.check_effects(self.path, "interaction-sync", {"effects":[effect]}, ["A1"]))

    def test_interaction_requires_persisted_identity_and_reconciliation(self):
        self.bind_workflow("interaction-sync")
        del self.inputs["sources"]["calls"]
        (self.path / "notes.txt").write_text("User-provided synthetic interaction notes.")
        self.inputs["sources"]["interaction"] = "notes.txt"
        self.bind_rows("reconciliation", {"people":[{"status":"matched", "source_refs":["notes.txt"]}], "source_refs":["notes.txt"]})
        self.save_inputs()
        self.assertFalse(runs.validate(self.root, self.path.name)["report_complete"])
        with (self.path / "request.md").open("a") as stream: stream.write("interaction_id: local:synthetic-id\n")
        checked = runs.validate(self.root, self.path.name)
        self.assertTrue(checked["report_complete"], checked["errors"])

    def test_status_flip_alone_cannot_validate(self):
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: draft", "status: ready"))
        self.assertFalse(runs.validate(self.root, self.path.name)["can_review"])

    def test_missing_binding_is_unvalidated(self):
        self.ready()
        (self.path / "inputs.json").unlink()
        checked = runs.validate(self.root, self.path.name)
        self.assertFalse(checked["ready_for_effects"])
        with self.assertRaises(ValueError): self.approve()

    def test_partial_review_can_finish_without_effect_permission(self):
        self.ready()
        self.inputs.update(sources={}, unavailable_sources=[{"name":"selected_call", "reason":"Calendar lookup failed; selected call unknown."}], effects=[])
        self.save_inputs()
        (self.path / "01_review.md").write_text("---\nstatus: ready\n---\n# Partial brief\nCalendar lookup failed. No call-specific findings or actions are supported.\n")
        checked = runs.validate(self.root, self.path.name)
        self.assertTrue(checked["can_review"])
        self.assertFalse(checked["report_complete"])
        review = runs.record_review(self.root, self.path.name, "Reviewer", "test", [])
        self.result(review, [])
        checked = runs.status(self.root, self.path.name)
        self.assertEqual(checked["state"], "completion_recorded")
        self.assertFalse(checked["ready_for_effects"])

    def test_automatic_source_snapshot_invalidates_on_raw_edit(self):
        self.ready(); self.approve()
        (self.path / "call.txt").write_text("Different call evidence")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_nested_normalized_source_references_are_frozen(self):
        self.ready()
        (self.path / "metadata.json").write_text(json.dumps({"source_refs":["call.txt"]}))
        (self.path / "selected.json").write_text(json.dumps({"call_id":"synthetic", "source_refs":["metadata.json"]}))
        self.approve()
        (self.path / "call.txt").write_text("Changed nested evidence")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_receipt_directory_inventory_is_frozen(self):
        self.ready()
        (self.path / "calls").mkdir()
        self.inputs["sources"]["calls"] = "calls"
        self.save_inputs(); self.approve()
        (self.path / "calls" / "new.txt").write_text("new receipt")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_source_escape_symlink_and_misspelling_rejected(self):
        self.ready()
        for sources in ({"selected_cal":"selected.json"}, {"selected_call":"../other.json"}, {"selected_call":"/tmp/other.json"}):
            self.inputs["sources"] = sources; self.save_inputs()
            self.assertFalse(runs.validate(self.root, self.path.name)["can_review"])
        (self.path / "linked").symlink_to(self.path / "selected.json")
        self.inputs["sources"] = {"selected_call":"linked"}; self.save_inputs()
        self.assertFalse(runs.validate(self.root, self.path.name)["can_review"])

    def test_call_prep_rejects_external_effect_and_payload_edit_stales(self):
        self.ready(); self.approve()
        self.inputs["effects"][0].update(operation="send", destination="mail")
        self.save_inputs()
        self.assertFalse(runs.validate(self.root, self.path.name)["ready_for_effects"])
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_pending_attempt_demands_reconciliation_and_cannot_replace_review(self):
        self.ready(); review = self.approve()
        self.result(review, [{"id":"A1", "status":"pending", "attempt_started_at":"2026-09-23T10:00:00Z"}])
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "recovery_required")
        with self.assertRaisesRegex(ValueError, "reconcile"):
            self.approve()

    def test_forecast_cannot_change_amount_or_stage(self):
        self.ready()
        for field in ("Amount", "StageName"):
            effect = {"id":"A1", "operation":"update", "destination":"Opportunity", "record_id":"o1",
                      "preimage":{field:None}, "payload":{field:100}, "source_refs":["call.txt"]}
            self.assertTrue(runs.check_effects(self.path, "forecast-weekly", {"effects":[effect]}, ["A1"]))

    def test_history_validation_cannot_be_omitted(self):
        self.ready()
        effect = {"id":"A1", "operation":"update", "destination":"Opportunity", "record_id":"o1",
                  "preimage":{"NextSteps":"9/1/26 SELLER - Preserved history."},
                  "payload":{"NextSteps":"9/23/26 SELLER - New action by 9/24/26."}, "source_refs":["call.txt"]}
        self.assertTrue(runs.check_effects(self.path, "pipeline-review", {"effects":[effect]}, ["A1"]))
        effect["history_operation"] = "prepend"
        effect["payload"]["NextSteps"] += "\n" + effect["preimage"]["NextSteps"]
        self.assertEqual(runs.check_effects(self.path, "pipeline-review", {"effects":[effect]}, ["A1"]), [])

    def test_apply_evidence_is_not_collection_snapshot_and_must_match(self):
        self.ready(); self.approve()
        directory = self.path / "effect-evidence"; directory.mkdir()
        effect = {"id":"E1", "operation":"update", "destination":"Contact", "record_id":"c1",
                  "preimage":{"Email":None}, "payload":{"Email":"buyer@example.org"}}
        evidence = {
            "preimage_reference":{"effect_id":"E1", "record_id":"c1", "observed_at":"2026-09-23T10:00:00Z", "fields":{"Email":None}},
            "provider_reference":{"effect_id":"E1", "record_id":"c1", "operation":"update", "destination":"Contact", "payload":effect["payload"]},
            "readback_reference":{"effect_id":"E1", "record_id":"c1", "observed_at":"2026-09-23T10:01:00Z", "fields":effect["payload"]}}
        result = {}
        for key, doc in evidence.items():
            ref = "effect-evidence/" + key + ".json"
            (self.path / ref).write_text(json.dumps(doc)); result[key] = ref
        runs.check_readback(self.path, effect, result, "2026-09-23T09:00:00Z")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_current")
        evidence["readback_reference"]["fields"] = {"Email":"wrong@example.org"}
        (self.path / result["readback_reference"]).write_text(json.dumps(evidence["readback_reference"]))
        with self.assertRaisesRegex(ValueError, "readback"):
            runs.check_readback(self.path, effect, result, "2026-09-23T09:00:00Z")

    def test_exact_json_comparison_distinguishes_false_zero_and_null_absence(self):
        self.assertFalse(runs.same_json({"Amount":0}, {"Amount":False}))
        self.assertFalse(runs.same_json({"Amount":1}, {"Amount":True}))
        self.assertFalse(runs.same_json({"Email":None}, {}))
        self.assertTrue(runs.same_json({"Amount":0,"IsPrimary":False}, {"IsPrimary":False,"Amount":0}))

    def test_run_ids_cannot_escape_or_overwrite(self):
        for bad in ("../escape", "UPPER", "x/y", ""):
            with self.assertRaises(ValueError):
                runs.init(self.root, bad, self.command)
        with self.assertRaises(ValueError):
            runs.init(self.root, self.path.name, self.command)

    def test_ready_requires_human_reference(self):
        self.ready()
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "awaiting_human_review")
        with self.assertRaises(ValueError):
            runs.record_review(self.root, self.path.name, "", "", [])

    def test_edit_invalidates_review(self):
        self.ready()
        self.approve()
        with (self.path / "01_review.md").open("a") as stream:
            stream.write("Changed recipient.\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_policy_edit_invalidates_review(self):
        self.ready()
        self.approve()
        policy = self.root / "_shared/policy.json"
        policy.write_text(policy.read_text() + "\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_reference_edit_invalidates_review(self):
        self.ready()
        self.approve()
        reference = self.root / "workflows/engagement/references/sales-call-prep-brief-formats.md"
        reference.write_text(reference.read_text() + "\nChanged brief requirement.\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_helper_edit_invalidates_review(self):
        self.ready()
        self.approve()
        helper = self.root / "scripts/mail_contact_stats.py"
        helper.write_text(helper.read_text() + "\n# changed\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_dependency_cannot_escape_repository(self):
        contract = self.root / "scripts/wrapper-contract.json"
        doc = json.loads(contract.read_text())
        doc["commands"][self.command]["review_inputs"] = ["scripts/../../outside.py"]
        contract.write_text(json.dumps(doc))
        with self.assertRaises(ValueError): wrappers.load_routes(self.root)

    def test_declared_missing_artifact_prevents_review_record(self):
        self.ready()
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: ready", 'status: ready\nartifacts: ["bundle.json"]'))
        with self.assertRaises(ValueError):
            self.approve()

    def test_changed_bundle_invalidates_review(self):
        self.ready()
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: ready", 'status: ready\nartifacts: ["bundle.json"]'))
        bundle = self.path / "bundle.json"
        bundle.write_text('{"source": "synthetic"}')
        self.approve()
        bundle.write_text('{"source": "different"}')
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_run_cannot_declare_another_runs_input(self):
        self.ready()
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: ready", 'status: ready\nartifacts: ["../other/bundle.json"]'))
        with self.assertRaises(ValueError):
            self.approve()

    def test_unsupported_or_duplicate_approval_rejected(self):
        self.ready()
        for ids in (["B2"], ["A1", "A1"]):
            with self.assertRaises(ValueError):
                runs.record_review(self.root, self.path.name, "Synthetic", "test", ids)

    def test_result_requires_provider_readback_reference(self):
        self.ready()
        review = self.approve()
        self.result(review, [{"id": "A1", "status": "verified", "provider_reference": "synthetic"}])
        with self.assertRaises(ValueError):
            runs.status(self.root, self.path.name)

    def test_unapproved_effect_not_accepted_in_result(self):
        self.ready()
        review = self.approve()
        self.result(review, [{"id": "B2", "status": "skipped"}])
        with self.assertRaises(ValueError):
            runs.status(self.root, self.path.name)

    def test_pending_result_is_incomplete(self):
        self.ready()
        review = self.approve()
        self.result(review, [{"id": "A1", "status": "pending"}])
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "incomplete")

    def test_complete_is_only_a_recorded_claim(self):
        self.ready()
        review = self.approve()
        self.result(review)
        state = runs.status(self.root, self.path.name)
        self.assertEqual(state["state"], "completion_recorded")
        self.assertIn("do not prove", state["note"])

    def test_another_run_cannot_supply_approval(self):
        self.ready()
        self.approve()
        other = runs.init(self.root, "synthetic-002", self.command)
        shutil.copyfile(self.path / "01_review.md", other / "01_review.md")
        shutil.copyfile(self.path / "review.json", other / "review.json")
        self.assertEqual(runs.status(self.root, other.name)["state"], "review_stale")

    def test_expected_configuration_change_is_not_unreviewed_drift(self):
        self.ready()
        target = "_shared/policy.json"
        changed = (self.root / target).read_text() + "\n"
        after = {"A1": {target: hashlib.sha256(changed.encode()).hexdigest()}}
        (self.path / "01_review.md").write_text("---\nstatus: ready\nexpected_after: " + json.dumps(after) + "\n---\n\n## Effect A1\nReviewed synthetic policy revision.\n")
        (self.path / "proposed-policy.json").write_text(changed)
        review = self.approve()
        (self.root / target).write_text(changed)
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "recovery_required")
        self.result(review)
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "completion_recorded")

    def test_local_change_different_from_reviewed_postimage_is_stale(self):
        self.ready()
        self.approve()
        (self.root / "_shared/adapters.md").write_text("Different adapter\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_route_escape_rejected(self):
        contract = self.root / "scripts/wrapper-contract.json"
        doc = json.loads(contract.read_text())
        doc["commands"][self.command]["workflow"] = "workflows/../../outside.md"
        contract.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):
            wrappers.load_routes(self.root)

    def test_wrapper_drift_and_missing_target_detected(self):
        wrapper = self.root / f".agents/skills/{self.command}/SKILL.md"
        wrapper.write_text("not a pointer")
        self.assertTrue(wrappers.render(self.root, check=True))
        self.assertFalse(wrappers.render(self.root))
        self.assertFalse(wrappers.render(self.root, check=True))
        target = self.root / wrappers.load_routes(self.root)[self.command]["workflow"]
        target.unlink()
        with self.assertRaises(ValueError):
            wrappers.render(self.root, check=True)

    def test_factory_checks_pass_without_runtime_data(self):
        errors, _ = check_repo.check(self.root)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
