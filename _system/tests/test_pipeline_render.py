"""Portable pipeline presentation and approval/receipt boundary regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
import test_coverage_check as coverage_fixture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'workflows/pipeline-review/scripts/pipeline_render.py'
spec = importlib.util.spec_from_file_location('pipeline_render', SCRIPT)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
EXPECTED = Path(__file__).parent / 'fixtures/pipeline_review_daily.json'


def evidence():
    return [{'date': '2026-09-28', 'source': 'Mail', 'who': 'Example Buyer',
             'title': 'Workshop follow-up', 'link': 'https://mail.example.org/message/1',
             'fact': 'Buyer requested the workshop outline by October 2.'}]


def task_change():
    return {'object': 'Task', 'id': 'task-1', 'name': 'Send workshop outline',
            'field': 'ActivityDate', 'current': '2026-09-28', 'proposed': '2026-10-02',
            'task_kind': 'reschedule', 'same_action': True}


def create_task():
    return {'object': 'Task', 'action': 'create', 'who_name': 'Example Buyer',
            'linkage_verified': True, 'candidates_refreshed': True,
            'fields': {'Subject': 'Confirm workshop attendees', 'ActivityDate': '2026-10-03',
                       'Status': 'open', 'WhoId': 'contact-1', 'WhatId': 'deal-1'}}


def base():
    return {'run': {'id': 'synthetic-run', 'date': '2026-09-28', 'branch': 'daily',
                    'coverage_scope': 'pipeline-daily', 'process_status': 'complete'},
            'counts': {'open': 4, 'in_scope': 3, 'reviewed': 3, 'skipped': 0, 'not_checked': 0},
            'deals': [{'id': 'deal-1', 'name': 'Example Workshop', 'flags': ['next_passed']},
                      {'id': 'deal-2', 'name': 'Example Studio', 'flags': ['blank_field']}],
            'blocks': [{'label': '1', 'deal': 'deal-1', 'status': 'proposed',
                        'next_step': {'current': 'Next: Send outline · Seller · 9/28/26',
                                      'proposed': '9/28/26 SELLER - Send the workshop outline by 10/2/26.'},
                        'changes': [task_change()], 'evidence': evidence()}],
            'questions': [{'label': 'Q1', 'deal': 'deal-2', 'status': 'open',
                           'context': 'Type is blank.', 'question': 'Which type applies?',
                           'next_step_current': None, 'evidence': evidence(),
                           'options': [{'label': 'Q1-a', 'text': 'New business', 'status': 'proposed',
                                        'changes': [{'object': 'Opportunity', 'id': 'deal-2', 'field': 'Type',
                                                     'current': None, 'proposed': 'New business'}]},
                                       {'label': 'Q1-b', 'text': 'Expansion', 'status': 'proposed',
                                        'changes': [{'object': 'Opportunity', 'id': 'deal-2', 'field': 'Type',
                                                     'current': None, 'proposed': 'Expansion'}]}]}],
            'writes': []}


def coverage(data):
    return {'scope': data['run']['coverage_scope'], 'ready': True, 'process_status': 'complete',
            'open_count': data['counts']['open'], 'in_scope': data['counts']['in_scope'],
            'lines': ['Coverage complete for the synthetic source scope.']}


def extended(data):
    data['run'].update(branch='extended', coverage_scope='pipeline')
    data['extended'] = {'rollup': {'stages': [{'stage': 'S2', 'count': 4, 'amount': '12000.50'}],
                                  'forecast': {'Likely': '8000.25', 'Unmapped': '4000.25'},
                                  'this_quarter': {'count': 4, 'amount': '12000.50'},
                                  'later': {'count': 0, 'amount': '0'}},
                        'since': '2026-09-21', 'delta': [],
                        'letters': [{'label': 'A', 'deal': 'deal-1', 'deal_name': 'Example Workshop',
                                     'status': 'proposed', 'basis': 'Buyer supplied decision date.',
                                     'change': {'object': 'Opportunity', 'id': 'deal-1', 'field': 'CloseDate',
                                                'current': '2026-09-30', 'proposed': '2026-10-02'},
                                     'evidence': evidence()}]}
    return data


class PipelineRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.policy = yaml.safe_load((ROOT / '_shared/policy.example.yaml').read_text())

    def call(self, mode, data, cov=None, *extra):
        review = self.directory / 'review.json'
        review.write_text(json.dumps(data))
        policy = self.directory / 'policy.yaml'
        policy.write_text(yaml.safe_dump(self.policy))
        args = [sys.executable, str(SCRIPT), mode, '--run', str(review), '--policy', str(policy)]
        if mode in {'report', 'notification'}:
            path = self.directory / 'coverage.json'
            path.write_text(json.dumps(coverage(data) if cov is None else cov))
            args += ['--coverage', str(path)]
        return subprocess.run(args + list(extra), capture_output=True, text=True)

    def ok(self, mode, data, cov=None, *extra):
        result = self.call(mode, data, cov, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def fails(self, mode, data, text, cov=None, *extra):
        result = self.call(mode, data, cov, *extra)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertIn(text, result.stderr)

    def test_daily_report_matches_reviewed_sample(self):
        self.assertEqual(self.ok('report', base()), json.loads(EXPECTED.read_text()))

    def test_empty_report_and_daily_silence(self):
        data = base(); data.update(deals=[], blocks=[], questions=[])
        out = self.ok('report', data)
        self.assertIn('No clear recommendations.', out)
        self.assertIn('No questions.', out)
        self.assertIn('No CRM changes proposed.', out)
        self.assertFalse(json.loads(self.ok('notification', data))['send'])

    def test_native_ids_and_source_fields_remain_portable(self):
        data = base(); data['blocks'][0]['changes'][0]['id'] = 'task/abc 1'
        out = self.ok('report', data)
        self.assertIn('/Task/task%2Fabc%201', out)
        self.assertIn('Next: Send outline', out)

    def test_html_display_preserves_proposed_text(self):
        data = base(); data['blocks'][0]['next_step']['current'] = '<p>Buyer&#39;s request<br>Second line</p>'
        out = self.ok('report', data)
        self.assertIn("Buyer's request\nSecond line", out)
        self.assertIn(data['blocks'][0]['next_step']['proposed'], out)

    def test_full_history_change_is_explicit_and_needs_both_fields(self):
        data = base(); step = data['blocks'][0]['next_step']
        step['proposed_full'] = step['proposed'] + '\nCorrected earlier entry.'
        self.fails('report', data, 'full-field changes need current_full')
        step['current_full'] = step['current'] + '\nEarlier entry.'
        out = self.ok('report', data)
        self.assertIn('history change proposed', out)
        self.assertIn(step['proposed_full'], out)
        self.assertNotIn('Older history stays unchanged.', out)

    def test_incomplete_sources_or_process_never_become_ready(self):
        data = base(); data['withheld'] = [{'deal': 'deal-1', 'reason': 'Missing mail.'}]; data['blocks'] = []
        cov = coverage(data); cov.update(ready=False, process_status='incomplete', lines=['Mail missing.'])
        out = self.ok('report', data, cov)
        self.assertIn('Withheld', out)
        self.assertEqual(json.loads(self.ok('notification', data, cov))['status'], 'incomplete')
        data = extended(base()); data['run'].update(process_status='incomplete', process_gaps=['Unreviewed evidence.'])
        self.assertEqual(json.loads(self.ok('notification', data))['status'], 'incomplete')

    def test_withheld_deal_cannot_remain_approvable(self):
        data = base(); data['withheld'] = [{'deal': 'deal-1', 'reason': 'Missing evidence.'}]
        self.fails('report', data, 'is withheld')

    def test_saved_coverage_must_match_scope_and_census(self):
        for patch, expected in [({'scope': 'forecast'}, 'coverage.scope'), ({'open_count': 90}, 'coverage.open_count')]:
            data = base(); cov = coverage(data); cov.update(patch)
            self.fails('report', data, expected, cov)

    def test_count_identity_and_missing_candidates_fail(self):
        data = base(); data['counts']['skipped'] = 2
        self.fails('report', data, 'in_scope must equal')
        data = base(); data['questions'] = []
        self.fails('report', data, 'flagged deals with no clear recommendation')

    def test_unflagged_task_and_pilot_candidates_do_not_invent_triggers(self):
        data = base(); data['deals'][0]['flags'] = []
        self.assertIn('1 flagged', self.ok('report', data))
        data = extended(base()); data['blocks'] = []; data['deals'][0]['flags'] = []
        data['extended']['letters'][0]['evidence'][0]['source'] = 'Pilot report'
        self.assertIn('Record proposals', self.ok('report', data))

    def test_duplicate_labels_and_unknown_dependencies_fail(self):
        data = base(); data['blocks'].append(copy.deepcopy(data['blocks'][0]))
        self.fails('report', data, 'already used')
        data = base(); data['blocks'][0]['depends_on_unknown'] = True
        self.fails('report', data, 'Needs your input')

    def test_alternatives_are_allowed_but_duplicates_within_block_or_option_fail(self):
        self.ok('question', base(), None, '--label', 'Q1')
        data = base(); extra = copy.deepcopy(data['blocks'][0]['changes'][0]); extra['proposed'] = '2026-10-04'
        data['blocks'][0]['changes'].append(extra)
        self.fails('report', data, 'already proposed')
        data = base(); option = data['questions'][0]['options'][0]
        option['changes'].append(copy.deepcopy(option['changes'][0]))
        self.fails('report', data, 'already proposed')

    def test_duplicate_fields_across_question_and_block_fail(self):
        data = base(); question = data['questions'][0]; question['deal'] = 'deal-1'
        question['options'][0]['changes'] = [task_change()]
        question['options'] = question['options'][:1]; data['deals'] = data['deals'][:1]
        self.fails('report', data, 'already proposed')

    def test_revised_question_keeps_old_label_and_next_unused_option(self):
        data = base(); options = data['questions'][0]['options']
        options[0].update(status='superseded', superseded_by='Q1-c')
        new = copy.deepcopy(options[1]); new.update(label='Q1-c', text='Replacement')
        options.append(new)
        out = self.ok('question', data, None, '--label', 'Q1')
        self.assertNotIn('- Q1-a', out); self.assertIn('- Q1-c', out)

    def test_multiple_creates_under_one_label_fail(self):
        data = base(); a = create_task(); b = copy.deepcopy(a); b['fields']['Subject'] = 'Another action'
        data['blocks'][0]['changes'] = [a, b]
        self.fails('report', data, 'at most one Task create')

    def test_two_alternatives_cannot_both_be_approved(self):
        data = base()
        for option in data['questions'][0]['options']:
            option['status'] = 'approved'
        self.fails('receipt', data, 'only one alternative')

    def test_create_fields_links_and_action_reuse_are_checked(self):
        for key in ('linkage_verified', 'candidates_refreshed'):
            data = base(); task = create_task(); task[key] = False; data['blocks'][0]['changes'] = [task]
            self.fails('report', data, key)
        data = base(); task = create_task(); task['fields']['Description'] = 'Undisplayed'; data['blocks'][0]['changes'] = [task]
        self.fails('report', data, 'not displayed')
        data = base(); data['blocks'][0]['changes'][0]['same_action'] = False
        self.fails('report', data, 'same_action')

    def test_letter_target_and_commercial_approval_boundary(self):
        data = extended(base()); out = self.ok('report', data)
        self.assertIn('A. [Example Workshop]', out)
        data['extended']['letters'][0]['change']['id'] = 'wrong-deal'
        self.fails('report', data, 'change targets')
        data = base(); data['blocks'][0]['changes'] = [extended(base())['extended']['letters'][0]['change']]
        self.fails('report', data, 'separate extended')

    def test_extended_currency_categories_and_date_follow_configuration(self):
        self.policy['reporting'].update(currency='EUR', amount_decimal_places=2, date_format='DD/MM/YYYY')
        out = self.ok('report', extended(base()))
        self.assertIn('28/09/2026', out); self.assertIn('Likely EUR 8,000.25', out)
        self.assertNotIn('$', out)

    def test_extended_notification_always_reports_actual_status(self):
        data = extended(base())
        self.assertEqual(json.loads(self.ok('notification', data))['status'], 'incomplete')
        data['questions'] = []; data['deals'] = data['deals'][:1]
        self.assertEqual(json.loads(self.ok('notification', data))['status'], 'ready')
        data.update(deals=[], blocks=[]); data['extended']['letters'] = []
        payload = json.loads(self.ok('notification', data))
        self.assertEqual((payload['send'], payload['status'], payload['delivery']), (True, 'complete', 'chat'))
        self.assertNotIn('channels', payload)

    def test_missing_approved_field_is_not_attempted(self):
        data = base(); data['blocks'][0]['status'] = 'partial'
        data['writes'] = [{'label': '1', 'object': 'Opportunity', 'id': 'deal-1', 'field': 'NextSteps', 'outcome': 'written'}]
        out = self.ok('receipt', data, None, '--labels', '1', '--final')
        self.assertIn('partial', out); self.assertIn('Not attempted', out)
        self.assertEqual(out.count('1 record fully written'), 2)

    def test_same_record_partial_fields_use_one_consistent_count(self):
        data = base(); block = data['blocks'][0]; block['status'] = 'partial'; block['next_step']['proposed'] = None
        extra = task_change(); extra.update(field='Subject', current='Old name', proposed='New name', task_kind='rename')
        block['changes'].append(extra)
        data['writes'] = [{'label': '1', 'object': 'Task', 'id': 'task-1', 'field': 'ActivityDate', 'outcome': 'written'}]
        out = self.ok('receipt', data, None, '--final')
        self.assertIn('partial', out); self.assertIn('Written', out); self.assertIn('Not attempted', out)
        self.assertEqual(out.count('0 records fully written'), 2)
        self.assertNotIn('1 record fully written', out)

    def test_approved_but_unattempted_label_is_in_receipt(self):
        data = base(); data['blocks'][0]['status'] = 'approved'
        out = self.ok('receipt', data, None, '--final')
        self.assertIn('not attempted', out); self.assertIn('NextSteps', out); self.assertIn('ActivityDate', out)

    def test_unknown_create_outcome_without_an_id_stays_unverified(self):
        data = base(); block = data['blocks'][0]; block['status'] = 'partial'
        block['next_step']['proposed'] = None; block['changes'] = [create_task()]
        data['writes'] = [{'label': '1', 'object': 'Task', 'id': None, 'field': 'create',
                           'outcome': 'unverified', 'detail': 'Request timed out; reconcile before retry.'}]
        out = self.ok('receipt', data, None, '--final')
        self.assertIn('Unverified', out); self.assertIn('0 records fully written', out)

    def test_unapproved_unlisted_and_repeated_successful_writes_fail(self):
        data = base(); write = {'label': '1', 'object': 'Task', 'id': 'task-1', 'field': 'ActivityDate', 'outcome': 'written'}
        data['writes'] = [write]; self.fails('receipt', data, 'only approved labels')
        data['blocks'][0]['status'] = 'approved'; write['id'] = 'unlisted'
        self.fails('receipt', data, 'not an approved change')
        write['id'] = 'task-1'; data['writes'].append(copy.deepcopy(write))
        self.fails('receipt', data, 'already written')

    def test_failed_then_verified_retry_uses_latest_outcome(self):
        data = base(); data['blocks'][0]['status'] = 'written'; data['blocks'][0]['next_step']['proposed'] = None
        write = {'label': '1', 'object': 'Task', 'id': 'task-1', 'field': 'ActivityDate', 'outcome': 'rejected', 'detail': 'Stale preimage.'}
        data['writes'] = [write, dict(write, outcome='written', detail='Verified after fresh approval.')]
        out = self.ok('receipt', data, None, '--final')
        self.assertEqual(out.count('1 record fully written'), 2)

    def test_malformed_input_has_no_partial_report(self):
        self.fails('report', [], 'invalid review input', {})

    def test_real_coverage_output_integrates_without_running_it_again(self):
        fixture = coverage_fixture.CoverageTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.ready()
        policy_path = self.directory / 'coverage-policy.yaml'; policy_path.write_text(yaml.safe_dump(fixture.policy))
        result = subprocess.run([sys.executable, str(ROOT / '_shared/scripts/coverage_check.py'), '--calls', str(fixture.calls),
                                 '--scope', 'pipeline-daily', '--since', fixture.since.isoformat(), '--json', '--policy', str(policy_path)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        cov = json.loads(result.stdout); data = base(); data.update(deals=[], blocks=[], questions=[])
        data['counts'].update(open=1, in_scope=1, reviewed=1)
        self.assertIn(cov['lines'][0], self.ok('report', data, cov))
        self.assertFalse(json.loads(self.ok('notification', data, cov))['send'])


if __name__ == '__main__':
    unittest.main()
