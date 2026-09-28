"""Meaningful setup, receipt, routing and native Calendar migration regressions."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
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
from configuration import CONTRACT_KEYS, LEGACY_PRIVATE, requirements
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
        policy = self.configured_policy()
        self.configure(['crm.read','mail.read','calendar.read'], policy)
        path = self.root / '_shared/policy.yaml'
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

    def configured_policy(self):
        policy = yaml.safe_load((self.root/'_shared/policy.example.yaml').read_text())
        policy['identity'].update(owner_id='test-owner', owner_email='seller@internal.example.org',
                                  internal_domains=['internal.example.org'], note_author='TEST')
        policy['crm']['record_url'] = 'https://crm.internal.example.org/{Object}/{Id}'
        for block, keys in [('crm', ['note_prefix','cooldown_marker']),
                            ('pipeline', ['note_next_line','note_history_line'])]:
            for key in keys:
                policy[block][key] = policy[block][key].replace('SELLER','TEST')
        policy['email_voice']['closing'] = 'Best, Test Person'
        policy['company'].update(name='Synthetic Workshop', product_name='Workshop Service')
        policy['pilot_usage']['pdf']['author'] = 'Synthetic Workshop'
        return policy

    def configure(self, capabilities, policy):
        (self.root/'_shared/policy.yaml').write_text(yaml.safe_dump(policy))
        config = {'version':2, 'mode':'configured', 'policy_sha256':sales_setup.policy_hash(self.root),
                  'field_mappings':{}, 'state_mappings':{},
                  'data_contracts': {name:{key:'Synthetic description; not live verification'
                                           for key in CONTRACT_KEYS[name]} for name in capabilities},
                  'capabilities':{name:{'status':'configured','provider':'synthetic',
                    'tool':'synthetic-test-tool', 'contract':'synthetic fixture',
                    'verified_at':datetime.now(timezone.utc).isoformat()}
                    for name in capabilities}}
        for name in wrappers.load_routes(self.root):
            required = requirements(name, policy, capabilities)
            for kind in ('field_mappings', 'state_mappings'):
                for group, keys in required[kind].items():
                    config[kind].setdefault(group, {}).update({key:'native.' + key for key in keys})
        self.save_adapters(config)
        return config

    def save_adapters(self, config):
        (self.root/'_shared/adapters.json').write_text(json.dumps(config))

    def test_supplied_pilot_export_does_not_require_crm_or_fiscal_setup(self):
        policy = self.configured_policy()
        for key in ['forecast', 'crm', 'pipeline']:
            policy.pop(key)
        self.configure(['usage.read'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'pilot-usage')['ready'])
        self.assertFalse(sales_setup.doctor(self.root, 'close')['ready'])

    def test_optional_close_integrations_only_block_their_effects(self):
        policy = self.configured_policy()
        self.configure(['crm.read','crm.write'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'close', effects=True)['ready'])
        policy['close']['handoff']['enabled'] = True
        policy['close']['provisioning']['enabled'] = True
        self.configure(['crm.read','crm.write'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'close')['ready'])
        self.assertFalse(sales_setup.doctor(self.root, 'close', effects=True)['ready'])
        self.assertTrue(sales_setup.doctor(self.root, 'close', effect=['crm.write'])['ready'])
        self.assertFalse(sales_setup.doctor(self.root, 'close', effect=['handoff.post'])['ready'])
        policy['close']['handoff'].update(destination='synthetic-destination', owners=['test-owner'])
        policy['close']['provisioning']['contract'] = 'Synthetic provisioning and recovery contract'
        self.configure(['crm.read','crm.write','handoff.post','provisioning.execute'], policy)
        self.assertTrue(sales_setup.doctor(self.root, 'close', effects=True)['ready'])

    def test_complete_synthetic_configuration_covers_every_route_and_effect(self):
        self.configure(list(CONTRACT_KEYS), self.configured_policy())
        for name in wrappers.load_routes(self.root):
            with self.subTest(workflow=name):
                result = sales_setup.doctor(self.root, name, effects=True)
                self.assertTrue(result['ready'], result)

    def test_malformed_settings_return_structured_failure(self):
        for body in ['identity: [broken', '[]', 'null']:
            with self.subTest(body=body):
                (self.root/'_shared/policy.yaml').write_text(body)
                result = sales_setup.doctor(self.root, 'close')
                self.assertFalse(result['ready'])
                self.assertTrue(result['errors'])
        for key in ['capabilities','field_mappings','state_mappings','data_contracts']:
            config = self.configure(list(CONTRACT_KEYS), self.configured_policy())
            config[key] = []
            self.save_adapters(config)
            self.assertFalse(sales_setup.doctor(self.root, 'close')['ready'], key)

    def test_required_contract_fields_and_capability_metadata_fail_closed(self):
        for kind, key in [('data_contracts','crm.read'),('field_mappings','Opportunity'),
                          ('state_mappings','Opportunity.state')]:
            config = self.configure(list(CONTRACT_KEYS), self.configured_policy())
            config[kind][key] = {}
            self.save_adapters(config)
            self.assertFalse(sales_setup.doctor(self.root, 'close')['ready'], (kind,key))
        for key, value in [('provider',None),('tool',[]),('verified_at','not-a-date'),
                           ('verified_at','2020-01-01T00:00:00'),
                           ('verified_at',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())]:
            config = self.configure(list(CONTRACT_KEYS), self.configured_policy())
            config['capabilities']['crm.read'][key] = value
            self.save_adapters(config)
            self.assertFalse(sales_setup.doctor(self.root, 'close')['ready'], (key,value))

    def test_incomplete_field_mapping_and_conditional_fields_are_rejected(self):
        policy = self.configured_policy()
        policy['pipeline']['conditional_fields'] = [{'field':'ReviewedTerms','when':{'Type':'Expansion'}}]
        config = self.configure(list(CONTRACT_KEYS), policy)
        del config['field_mappings']['Opportunity']['ReviewedTerms']
        self.save_adapters(config)
        self.assertFalse(sales_setup.doctor(self.root, 'pipeline-review')['ready'])
        self.assertTrue(sales_setup.doctor(self.root, 'forecast-weekly')['ready'])
        config['field_mappings'] = {'Id':'id'}
        config['state_mappings'] = {'open':'open'}
        self.save_adapters(config)
        self.assertFalse(sales_setup.doctor(self.root, 'close')['ready'])

    def test_policy_inconsistency_placeholders_and_obsolete_mode_are_rejected(self):
        cases = [('pipeline','stage_order',['S2','S2']), ('pipeline','conditional_fields',3),
                 ('pipeline','stage_entry',{}), ('crm','record_url','https://crm.example.com/{Id}'),
                 ('identity','note_author','SELLER'), ('forecast','fiscal_year_start_month',13),
                 ('reporting','amount_decimal_places',-1), ('followup','cooldown_days',-1),
                 ('pilot_usage','usage_decimal_places',-1), ('company','name','Example Company')]
        for block,key,value in cases:
            with self.subTest(block=block,key=key):
                policy=self.configured_policy();policy[block][key]=value
                self.configure(list(CONTRACT_KEYS),policy)
                self.assertFalse(sales_setup.doctor(self.root)['ready'])
        for change in ['remove_pipeline','obsolete_mode']:
            policy=self.configured_policy()
            if change=='remove_pipeline': policy.pop('pipeline')
            else: policy['mode']='configured'
            self.configure(list(CONTRACT_KEYS),policy)
            self.assertFalse(sales_setup.doctor(self.root,'interaction-sync')['ready'])

    def test_selected_effects_cannot_bypass_route_or_enabled_policy(self):
        config=self.configure(['crm.read','mail.read','calendar.read','crm.write'],self.configured_policy())
        self.assertTrue(sales_setup.doctor(self.root,'interaction-sync',effect=['crm.write'])['ready'])
        self.assertFalse(sales_setup.doctor(self.root,'interaction-sync',effect=['mail.draft'])['ready'])
        self.assertFalse(sales_setup.doctor(self.root,'interaction-sync',effect=['crm.write','mail.draft'])['ready'])
        for name, effects in [('sales-call-prep',['crm.write']),('close',['mail.draft']),
                              ('close',['handoff.post']), (None,['crm.write'])]:
            self.assertFalse(sales_setup.doctor(self.root,name,effect=effects)['ready'])

    def test_missing_selected_helper_is_rejected(self):
        policy=self.configured_policy()
        policy['tooling']['scripts']['forecast_math']='missing.py'
        self.configure(list(CONTRACT_KEYS),policy)
        self.assertFalse(sales_setup.doctor(self.root,'forecast-weekly')['ready'])
        self.assertTrue(sales_setup.doctor(self.root,'pilot-usage')['ready'])

    def test_legacy_files_preserved_ignored_and_rejected_if_distributed(self):
        for rel in LEGACY_PRIVATE:
            path=self.root/rel;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('private legacy data')
        output=sales_setup.initialize(self.root)
        self.assertEqual(sum('legacy private settings preserved:' in x for x in output),3)
        for rel in LEGACY_PRIVATE:
            self.assertEqual((self.root/rel).read_text(),'private legacy data')
            self.assertTrue(any(rel in e for e in check_repo.check(self.root)[0]))
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        for rel in LEGACY_PRIVATE:
            self.assertEqual(subprocess.run(['git','check-ignore','-q',rel],cwd=self.root).returncode,0)
        self.assertEqual(check_repo.check(self.root)[0],[])
        subprocess.run(['git','add','-f',*sorted(LEGACY_PRIVATE)],cwd=self.root,check=True)
        errors=check_repo.check(self.root)[0]
        self.assertEqual(sum('private/runtime material included:' in e for e in errors),3)

    def test_public_checks_reject_source_branding_and_custom_api_fields(self):
        target = self.root/'example.md'
        target.write_text('perplex' + 'ity')
        self.assertTrue(any('source-specific' in error for error in check_repo.check(self.root)[0]))
        target.write_text('InternalField' + '__c')
        self.assertTrue(any('custom API field' in error for error in check_repo.check(self.root)[0]))

    def test_reads_header_dependencies_must_exist(self):
        self.assertEqual(check_repo.dependency_errors(self.root, wrappers.load_routes(self.root)), [])
        path = self.root/'workflows/interaction-sync/procedure.md'
        path.write_text(path.read_text().replace('../task-triage-speed-run/references/crm-corrections.md', 'references/'))
        errors = check_repo.dependency_errors(self.root, wrappers.load_routes(self.root))
        self.assertTrue(any('interaction-sync: missing or external reads dependency: references/' in e for e in errors))


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
