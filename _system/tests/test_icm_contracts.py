"""Contract regressions: fail on broken loading or misplaced approval checkpoints."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '_system/scripts'))
from contract_checks import contract_errors
from wrappers import load_routes


class ContractChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            '.git', '.venv', '__pycache__', 'policy.yaml', 'adapters.json'))
        self.routes = load_routes(self.root)
        self.path = self.root / 'workflows/pipeline-review/CONTEXT.md'

    def errors(self):
        return contract_errors(self.root, self.routes)

    def test_current_contracts_and_starter_shape(self):
        self.assertEqual(self.errors(), [])
        starter = (self.root / '_system/docs/workflow-context-template.md').read_text()
        for heading in ('Inputs', 'Process', 'Checkpoints', 'Audit', 'Outputs'):
            self.assertIn('## ' + heading, starter)
        self.assertNotIn('## Checkpoints', (self.root / 'workflows/sales-call-prep/CONTEXT.md').read_text())

    def test_table_and_audit_regressions_fail(self):
        self.path.write_text(self.path.read_text().replace('Section/Scope | Why', 'Load')
                             .replace('## Audit', '## Removed audit'))
        errors = self.errors()
        self.assertTrue(any('invalid Inputs table' in e for e in errors))
        self.assertTrue(any('contract sections' in e for e in errors))

    def test_global_reference_rules_remain_in_scoped_routes(self):
        for name in ('sales-call-prep', 'interaction-sync', 'task-triage-speed-run',
                     'pipeline-review', 'forecast-weekly'):
            text = (self.root / f'workflows/{name}/CONTEXT.md').read_text()
            inputs = text.split('## Inputs', 1)[1].split('## Process', 1)[0]
            self.assertIn('opening of "Process"', inputs)
            self.assertIn('"Outputs and readiness"', inputs)
            self.assertIn('"Human check"', inputs)
        for name in ('sales-call-prep', 'pipeline-review'):
            self.assertIn('"All modes"', (self.root / f'workflows/{name}/CONTEXT.md').read_text())

    def test_bad_scoped_heading_and_missing_reference_fail(self):
        self.path.write_text(self.path.read_text().replace('"Daily review"', '"Nonexistent branch"')
                             .replace('(references/report-format.md)', '(references/missing.md)'))
        errors = self.errors()
        self.assertTrue(any('missing scoped section' in e for e in errors))
        self.assertTrue(any('missing or external input reference' in e for e in errors))

    def test_checkpoint_cannot_name_missing_step(self):
        self.path.write_text(self.path.read_text().replace('| 3 | Report,', '| 99 | Report,'))
        self.assertTrue(any('checkpoint names a missing step' in e for e in self.errors()))

    def test_size_and_orphan_checks_fail(self):
        self.path.write_text(self.path.read_text() + '\n' * 81)
        ref = self.path.parent / 'references/unrouted.md'
        ref.write_text('# Unrouted\n' * 201)
        errors = self.errors()
        for expected in ('exceeds 80', 'exceeds 200', 'unrouted reference'):
            self.assertTrue(any(expected in e for e in errors), expected)

    def test_relationship_definition_preserves_unknown_and_held_meeting(self):
        rules = (self.root / '_shared/rules.md').read_text()
        definition = rules.split('<a id="contact_status">', 1)[1].split('<a id=', 1)[0]
        for phrase in ('verified held meeting', 'scheduled invitation alone',
                       'leave status unknown', 'Active and unknown Contacts never recycle'):
            self.assertIn(phrase, definition)
        for name in ('interaction-sync', 'task-triage-speed-run'):
            self.assertIn('rules#contact_status', (self.root / f'workflows/{name}/references/procedure.md').read_text())

    def test_pilot_identity_read_and_export_only_boundary(self):
        collect = (self.root / 'workflows/pipeline-review/references/collect.md').read_text()
        identity = collect.split('## Pilot report identity', 1)[1]
        for phrase in ('Only in extended mode when the user supplies', 'AccountId',
                       'mapped fields', 'original response', 'needs-input', 'rules#pilot_handoff',
                       'policy.pipeline.in_scope_stages', 'update the scope and coverage before proposing'):
            self.assertIn(phrase, identity)
        source = (self.root / 'workflows/pilot-usage/references/report-format.md').read_text()
        self.assertIn('CRM linkage unverified', source)
        self.assertIn('without adding CRM prerequisites to export-only reports', source)
        forecast = (self.root / 'workflows/forecast-weekly/CONTEXT.md').read_text()
        self.assertNotIn('rules#pilot_handoff', forecast)
        self.assertIn('without analytics reads or loading pilot reports', forecast)


if __name__ == '__main__':
    unittest.main()
