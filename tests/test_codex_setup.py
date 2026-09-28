"""Meaningful setup, receipt, routing and native Calendar migration regressions."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import wrappers
import run
import receipts
import check_repo
# Avoid importing an unrelated installed module named setup.
spec = importlib.util.spec_from_file_location('sales_setup', ROOT / 'scripts/setup.py')
sales_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sales_setup)
import test_coverage_check as coverage_fixture


class NativeSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'repo'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git','.venv','__pycache__','policy.yaml','adapters.json'))

    def test_initialization_preserves_edits_and_doctor_blocks_all_seven(self):
        sales_setup.initialize(self.root)
        path = self.root / '_shared/policy.yaml'
        path.write_text(path.read_text() + '\n# preserved local edit\n')
        original = path.read_bytes()
        self.assertTrue(all('preserved' in row for row in sales_setup.initialize(self.root)))
        self.assertEqual(original, path.read_bytes())
        result = sales_setup.doctor(self.root)
        self.assertFalse(result['ready'])
        self.assertEqual(len(result['workflows']), 7)
        self.assertTrue(all(row['missing'] for row in result['workflows'].values()))

    def test_missing_configuration_reports_gap(self):
        self.assertFalse(sales_setup.doctor(self.root)['ready'])

    def test_policy_changes_invalidate_review_and_effects_are_separate(self):
        sales_setup.initialize(self.root)
        path = self.root / '_shared/policy.yaml'
        policy = yaml.safe_load(path.read_text())
        policy['identity'].update(owner_id='test-owner', owner_email='seller@internal.example.org')
        path.write_text(yaml.safe_dump(policy))
        config = {'version':2, 'field_mappings':{'Id':'id'}, 'state_mappings':{'open':'open'}, 'mode':'configured', 'policy_sha256':sales_setup.policy_hash(self.root),
                  'capabilities':{name:{'status':'configured','tool':'synthetic-test-tool',
                     'contract':'synthetic mapping, not a live check','verified_at':'2026-09-27T10:00:00Z'}
                     for name in ['crm.read','mail.read','calendar.read']}}
        (self.root/'_shared/adapters.json').write_text(json.dumps(config))
        self.assertTrue(sales_setup.doctor(self.root, 'interaction-sync')['ready'])
        self.assertFalse(sales_setup.doctor(self.root, 'interaction-sync', effects=True)['ready'])
        path.write_text(path.read_text() + '\n# changed\n')
        self.assertFalse(sales_setup.doctor(self.root, 'interaction-sync')['ready'])

    def test_symlink_configuration_refused_before_any_write(self):
        outside = self.base/'outside'; outside.write_text('unchanged')
        (self.root/'_shared/adapters.json').symlink_to(outside)
        with self.assertRaises(ValueError): sales_setup.initialize(self.root)
        self.assertFalse((self.root/'_shared/policy.yaml').exists())
        self.assertEqual(outside.read_text(), 'unchanged')

    def test_pointer_drift_and_symlinked_ancestor_fail(self):
        pointer = self.root/'.agents/skills/close/SKILL.md'
        pointer.write_text('drift')
        self.assertTrue(wrappers.render(self.root, check=True))
        shutil.rmtree(self.root/'.agents/skills/close')
        outside = self.base/'outside';outside.mkdir()
        (self.root/'.agents/skills/close').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):wrappers.render(self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_all_seven_run_directories_are_unique_and_external(self):
        paths = [run.initialize(name, self.base/'runs', self.root) for name in wrappers.load_routes(self.root)]
        self.assertEqual(len(set(paths)), 7)
        for path in paths:
            self.assertNotIn(self.root, path.parents)
            self.assertTrue((path/'calls').is_dir())
            self.assertTrue((path/'raw').is_dir())
        self.assertNotEqual(run.initialize('close', self.base/'runs', self.root), paths[-1])
        with self.assertRaises(ValueError):run.initialize('close', self.root/'runs', self.root)
        (self.base/'linked').symlink_to(self.base/'runs', target_is_directory=True)
        with self.assertRaises(ValueError):run.initialize('close', self.base/'linked', self.root)

    def test_export_inventory_is_scoped_and_excludes_private_configuration(self):
        sales_setup.initialize(self.root)
        files = {str(p) for p in check_repo.public_files(self.root)}
        self.assertNotIn('_shared/policy.yaml', files)
        self.assertIn('.agents/skills/close/SKILL.md', files)
        self.assertIn('_shared/policy.example.yaml', files)

    def configure(self, capabilities, policy):
        (self.root/'_shared/policy.yaml').write_text(yaml.safe_dump(policy))
        config = {'version':2, 'mode':'configured', 'policy_sha256':sales_setup.policy_hash(self.root),
                  'field_mappings':{'Id':'id'}, 'state_mappings':{'open':'open'},
                  'capabilities':{name:{'status':'configured','tool':'synthetic-test-tool',
                    'contract':'synthetic fixture','verified_at':'2026-09-27T10:00:00Z'}
                    for name in capabilities}}
        (self.root/'_shared/adapters.json').write_text(json.dumps(config))

    def test_supplied_pilot_export_does_not_require_crm_or_fiscal_setup(self):
        policy = yaml.safe_load((self.root/'_shared/policy.example.yaml').read_text())
        policy.pop('forecast')
        self.configure(['usage.read'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'pilot-usage')['ready'])
        self.assertFalse(sales_setup.doctor(self.root, 'close')['ready'])

    def test_optional_close_integrations_only_block_their_effects(self):
        policy = yaml.safe_load((self.root/'_shared/policy.example.yaml').read_text())
        policy['identity'].update(owner_id='test-owner', owner_email='seller@internal.example.org')
        self.configure(['crm.read','crm.write'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'close', effects=True)['ready'])
        policy['close']['handoff']['enabled'] = True
        policy['close']['provisioning']['enabled'] = True
        self.configure(['crm.read','crm.write'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'close')['ready'])
        self.assertFalse(sales_setup.doctor(self.root, 'close', effects=True)['ready'])
        policy['close']['handoff'].update(destination='synthetic-destination', owners=['test-owner'])
        policy['close']['provisioning']['contract'] = 'Synthetic provisioning and recovery contract'
        self.configure(['crm.read','crm.write','handoff.post','provisioning.execute'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'close', effects=True)['ready'])

    def test_public_checks_reject_source_branding_and_custom_api_fields(self):
        target = self.root/'example.md'
        target.write_text('perplex' + 'ity')
        self.assertTrue(any('source-specific' in error for error in check_repo.check(self.root)[0]))
        target.write_text('InternalField' + '__c')
        self.assertTrue(any('custom API field' in error for error in check_repo.check(self.root)[0]))


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.run = run.initialize('sales-call-prep', self.base/'runs')
        self.start = datetime.now(timezone.utc).isoformat()
        self.raw_in = self.base/'request.json';self.raw_in.write_text('{"query":"example"}\n')
        self.raw_out = self.base/'response.json';self.raw_out.write_text('{"messages":[],"nextPageToken":null}\n')
        self.normal = self.base/'normalized.json';self.normal.write_text(json.dumps({
            'input':{'tool_name':'search_email','arguments':{'queries':['example'],'cursor':None}},
            'output':{'result':{'email_results':{'emails':[], 'next_cursor':None}}}}))

    def capture(self, call_id='a', start=None):
        return receipts.capture(self.run, call_id, self.raw_in, self.raw_out, self.normal,
            start or self.start, datetime.now(timezone.utc).isoformat(), 'synthetic.provider')

    def test_capture_preserves_raw_bytes_and_rejects_duplicate(self):
        self.capture()
        self.assertEqual((self.run/'raw/output_a.json').read_bytes(), self.raw_out.read_bytes())
        self.assertEqual(receipts.verify(self.run), [])
        with self.assertRaises(ValueError):self.capture()

    def test_tampered_normalization_and_orphan_calls_are_detected(self):
        self.capture()
        (self.run/'calls/output_a.json').write_text('{}')
        self.assertTrue(receipts.verify(self.run))
        (self.run/'calls/input_orphan.json').write_text('{}')
        self.assertIn('unbound or missing normalized calls', receipts.verify(self.run))

    def test_stale_future_naive_times_fail(self):
        for time in [(datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),
                     (datetime.now(timezone.utc)+timedelta(days=1)).isoformat(), '2026-09-27T10:00:00']:
            with self.assertRaises(ValueError):self.capture(start=time)
        self.assertEqual(list((self.run/'calls').iterdir()), [])

    def test_raw_symlinks_and_modified_raw_evidence_fail(self):
        link=self.base/'linked.json';link.symlink_to(self.raw_out)
        self.raw_out=link
        with self.assertRaises(ValueError):self.capture()
        self.raw_out=link.resolve();self.capture()
        (self.run/'raw/output_a.json').write_text('tampered')
        self.assertTrue(receipts.verify(self.run))

    def test_missing_receipts_are_not_ready(self):
        self.assertTrue(receipts.verify(self.run))


class NativeCalendarTests(unittest.TestCase):
    def setUp(self):
        self.fixture = coverage_fixture.CoverageTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_native_page_chain_requires_all_pages(self):
        f=self.fixture;f.ready()
        path=f.calls/'output_calendar.json';doc=json.loads(path.read_text())
        doc['result']['next_cursor']='page2';path.write_text(json.dumps(doc))
        from coverage_check import check
        self.assertFalse(check(f.calls,f.policy,f.since,'pipeline-daily')['ready'])
        inp=json.loads((f.calls/'input_calendar.json').read_text());inp['arguments']['cursor']='page2'
        (f.calls/'input_calendar2.json').write_text(json.dumps(inp))
        doc['result']['next_cursor']=None
        (f.calls/'output_calendar2.json').write_text(json.dumps(doc))
        self.assertTrue(check(f.calls,f.policy,f.since,'pipeline-daily')['ready'])
