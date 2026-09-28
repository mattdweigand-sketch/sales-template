"""Portable pilot metrics, source binding and report output regressions."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workflows/pilot-usage/scripts'))
sys.path.insert(0,str(ROOT / '_system/scripts'))
import pilot_usage
import receipts
import run


class PilotFixture:
    def setUp(self):
        self.policy=yaml.safe_load((ROOT/'_shared/policy.example.yaml').read_text())
        self.review={'reviewed':True,'account_id':'example-account','customer_name':'Example Customer',
          'prepared_by':'Example Seller','pilot_start':'2026-09-01','pilot_end':'2026-09-30',
          'data_through':'2026-09-20','categories':{},'interpretation':'Synthetic activity only.'}
        self.roster=[{'id':'user-1','name':'Example User'},{'id':'user-2','name':'Idle User'}]
        self.activity=[{'id':'activity-1','user_id':'user-1','date':'2026-09-02','quantity':'0.005','unit':'units'},
                       {'id':'activity-2','user_id':'user-1','date':'2026-09-03','quantity':'0.005','unit':'units'}]

    def compute(self):return pilot_usage.compute(self.review,self.roster,self.activity,self.policy)


class PilotTests(PilotFixture, unittest.TestCase):
    def test_exact_sum_then_display_rounding_and_idle_users(self):
        report=self.compute()
        self.assertEqual(report['total_quantity'],'0.01')
        self.assertEqual(report['active_users'],1)
        self.assertEqual(report['roster_size'],2)
        self.assertEqual(report['users'][0]['active_days'],2)

    def test_another_company_product_unit_and_precision(self):
        self.policy['company']={'name':'Example Workshop','product_name':'Design Service'}
        self.policy['pilot_usage'].update(usage_unit='hours',usage_decimal_places=3)
        for row in self.activity:row['unit']='hours'
        report=self.compute()
        self.assertEqual(report['total_quantity'],'0.010')
        self.assertEqual(report['product'],'Design Service')
        self.assertEqual(report['usage_unit'],'hours')

    def test_large_values_preserve_small_contributions(self):
        self.activity[0]['quantity']='123456789012345678901234567890.005'
        self.assertEqual(self.compute()['total_quantity'],'123456789012345678901234567890.01')

    def test_mixed_missing_negative_nonfinite_and_boolean_units_fail(self):
        for key,value in [('unit','hours'),('unit',None),('quantity','-1'),('quantity','NaN'),
                          ('quantity','Infinity'),('quantity',True),('quantity',None)]:
            with self.subTest(key=key,value=value):
                rows=deepcopy(self.activity);rows[0][key]=value
                with self.assertRaises(ValueError):pilot_usage.compute(self.review,self.roster,rows,self.policy)

    def test_duplicates_unknown_users_and_out_of_window_fail(self):
        for key,value in [('id','activity-2'),('user_id','missing'),('date','2026-10-01')]:
            rows=deepcopy(self.activity);rows[0][key]=value
            with self.assertRaises(ValueError):pilot_usage.compute(self.review,self.roster,rows,self.policy)
        with self.assertRaises(ValueError):pilot_usage.compute(self.review,self.roster*2,self.activity,self.policy)

    def test_unreviewed_invalid_dates_and_unknown_categories_fail(self):
        for changes in [{'reviewed':False},{'reviewed':'true'},{'pilot_start':'2026-10-01'},
                        {'categories':{'missing':'Imagined work'}}]:
            with self.assertRaises(ValueError):pilot_usage.compute({**self.review,**changes},self.roster,self.activity,self.policy)

    def test_html_escapes_content_and_needs_no_remote_assets(self):
        self.review['customer_name']='<script>bad</script>'
        html=pilot_usage.render(self.compute(),self.policy)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertNotIn('https://',html)
        self.assertNotIn('@font-face',html)
        self.assertIn('Example Product',html)


class PilotReceiptTests(PilotFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.run=run.initialize('pilot-usage',self.base/'runs')

    def capture(self,name,selection,rows,**extra):
        args={'query_id':name,'source':'usage','selection':selection,'owner_id':'synthetic-owner',
          'provider_query':'Synthetic export fixture','cursor':None,'account_id':self.review['account_id'],
          'timezone':'UTC',**extra}
        normal={'input':{'arguments':args},'output':{'result':{'status':'success','records':rows,
          'total_count':len(rows),'next_cursor':None}}}
        request=self.base/(name+'-request.json');request.write_text(json.dumps(args))
        response=self.base/(name+'-response.json');response.write_text(json.dumps(rows))
        path=self.base/(name+'-normalized.json');path.write_text(json.dumps(normal))
        now=datetime.now(timezone.utc).isoformat()
        receipts.capture(self.run,name,request,response,path,now,now,'synthetic-file')

    def sources(self,account=None,unit='units'):
        self.capture('roster','pilot_roster',self.roster,as_of=self.review['data_through'])
        self.capture('activity','pilot_activity',self.activity,start_date=self.review['pilot_start'],
          end_date='2026-09-21',unit=unit,**({'account_id':account} if account else {}))

    def test_complete_receipts_collect_and_compute(self):
        self.sources()
        roster,activity=pilot_usage.collect(self.run,self.review,'roster','activity',self.policy)
        self.assertEqual(pilot_usage.compute(self.review,roster,activity,self.policy)['total_quantity'],'0.01')

    def test_wrong_account_is_rejected(self):
        self.sources(account='unrelated-account')
        with self.assertRaisesRegex(ValueError,'account/selection'):pilot_usage.collect(self.run,self.review,'roster','activity',self.policy)

    def test_wrong_unit_and_tampered_source_are_rejected(self):
        self.sources(unit='hours')
        with self.assertRaisesRegex(ValueError,'unit mismatch'):pilot_usage.collect(self.run,self.review,'roster','activity',self.policy)
        (self.run/'raw/output_activity.json').write_text('changed')
        with self.assertRaisesRegex(ValueError,'receipt verification'):pilot_usage.collect(self.run,self.review,'roster','activity',self.policy)

    def test_missing_terminal_page_and_wrong_window_are_rejected(self):
        self.sources()
        with self.assertRaisesRegex(ValueError,'window mismatch'):
            pilot_usage.collect(self.run,{**self.review,'pilot_start':'2026-09-02'},'roster','activity',self.policy)
        (self.run/'calls/output_activity.json').unlink()
        with self.assertRaises(ValueError):pilot_usage.collect(self.run,self.review,'roster','activity',self.policy)


class PilotRendererTests(PilotFixture, unittest.TestCase):
    def test_browser_job_completion_does_not_require_browser_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.pdf'
            command=[sys.executable,'-c',
                'import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); p.write_bytes(b"candidate"); '
                'print("9 bytes written to file "+str(p),flush=True); time.sleep(30)',str(candidate)]
            pilot_usage.run_renderer(command,candidate,5)
            self.assertEqual(candidate.read_bytes(),b'candidate')

    def test_partial_file_without_completion_signal_times_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.pdf'
            command=[sys.executable,'-c',
                'import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_bytes(b"partial"); time.sleep(30)',
                str(candidate)]
            with self.assertRaisesRegex(ValueError,'timed out'):
                pilot_usage.run_renderer(command,candidate,0.3)

    def test_unreadable_candidate_preserves_existing_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);html=root/'report.html';html.write_text('<p>Example</p>')
            output=root/'report.pdf';output.write_bytes(b'existing report')
            def incomplete(command,candidate,timeout):
                candidate.write_bytes(b'%PDF-1.7\npartial')
            with mock.patch.object(pilot_usage,'run_renderer',side_effect=incomplete):
                with self.assertRaisesRegex(ValueError,'unreadable'):
                    pilot_usage.print_pdf(html,output,self.policy,renderer=sys.executable)
            self.assertEqual(output.read_bytes(),b'existing report')
