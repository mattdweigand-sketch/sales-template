"""Forecast chat readiness follows actual coverage and workflow review status."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import yaml
import test_coverage_check as coverage_fixture

ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=ROOT/'workflows/forecast-weekly/scripts'
sys.path.insert(0,str(SCRIPTS))
from forecast_notify import build_payload


class ForecastNotifyTests(unittest.TestCase):
    def setUp(self):
        self.f=coverage_fixture.CoverageTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.policy=self.f.calls/'policy.yaml';self.policy.write_text(yaml.safe_dump(self.f.policy))

    def notify(self):
        return subprocess.run([sys.executable,str(SCRIPTS/'forecast_notify.py'),'--since',self.f.since.isoformat(),
          '--calls',str(self.f.calls),'--policy',str(self.policy)],capture_output=True,text=True)

    def test_ready_only_after_complete_coverage(self):
        self.f.ready('forecast')
        result=self.notify();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['title'],'Weekly forecast ready')
        (self.f.calls/'output_calendar.json').unlink()
        self.assertEqual(json.loads(self.notify().stdout)['title'],'Weekly forecast incomplete')

    def test_no_snapshot_is_incomplete(self):
        self.assertEqual(json.loads(self.notify().stdout)['title'],'Weekly forecast incomplete')

    def test_process_review_can_withhold_ready(self):
        good=json.dumps({'ready':True,'process_status':'complete','lines':[]})
        self.assertEqual(build_payload(0,good,'','',None,'review-needed')['title'],'Weekly forecast incomplete')
        self.assertEqual(build_payload(1,good,'','',None)['title'],'Weekly forecast incomplete')
        self.assertEqual(build_payload(0,json.dumps({'ready':False}),'','',None)['title'],'Weekly forecast incomplete')
