#!/usr/bin/env python3
"""Compute a vendor-neutral pilot report from complete normalized usage receipts."""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '_shared/scripts'))
sys.path.insert(0, str(ROOT / '_system/scripts'))
from coverage_check import load_queries, stamp
from receipts import verify
from run import external_path


def quantity(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('quantity must be an explicit decimal string')
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('invalid quantity') from exc
    if not number.is_finite() or number < 0:
        raise ValueError('quantity must be finite and non-negative')
    return number


def number(value, places):
    return format(value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), 'f')


def compute(review, roster, activity, policy):
    if not isinstance(roster, list) or not isinstance(activity, list):
        raise ValueError('roster and activity must be lists')
    if any(not isinstance(row, dict) for row in roster + activity):
        raise ValueError('roster and activity rows must be objects')
    amounts = [quantity(row.get('quantity')) for row in activity]
    # Cover both integer and fractional digits, plus carry from summing all rows.
    lower = min([0, -6] + [n.as_tuple().exponent for n in amounts])
    upper = max([0] + [n.adjusted() for n in amounts])
    with localcontext() as context:
        context.prec = max(28, upper - lower + len(str(len(amounts))) + 2)
        return _compute(review, roster, activity, policy)


def _compute(review, roster, activity, policy):
    if review.get('reviewed') is not True:
        raise ValueError('reviewed must be Boolean true; local metadata does not replace chat approval')
    for key in ['account_id','customer_name','prepared_by']:
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError('missing ' + key)
    start, end, through = [date.fromisoformat(review[k]) for k in ['pilot_start','pilot_end','data_through']]
    if not start <= through <= end or start >= end:
        raise ValueError('invalid pilot/report window')
    cfg = policy['pilot_usage']
    places = cfg['usage_decimal_places']
    if type(places) is not int or not 0 <= places <= 6 or not cfg['usage_unit']:
        raise ValueError('configure a unit and 0..6 decimal places')
    users = {}
    for row in roster:
        if not isinstance(row.get('id'),str) or not row['id'] or row['id'] in users:
            raise ValueError('roster IDs must be nonempty and unique')
        users[row['id']] = {'id':row['id'],'name':row.get('name') or row['id'],
                            'records':0,'quantity':Decimal(0),'days':set()}
    seen, categories = set(), defaultdict(lambda: Decimal(0))
    for row in activity:
        key = row.get('id')
        if not isinstance(key,str) or not key or key in seen:
            raise ValueError('activity IDs must be nonempty and unique')
        seen.add(key)
        if row.get('user_id') not in users:
            raise ValueError('activity user is not in the reviewed roster')
        day = date.fromisoformat(row['date'])
        if not start <= day <= through:
            raise ValueError('activity outside the report window')
        if row.get('unit') != cfg['usage_unit']:
            raise ValueError('mixed or missing units; normalize with evidenced conversion before aggregation')
        amount = quantity(row.get('quantity'))
        user = users[row['user_id']]
        user['records'] += 1; user['quantity'] += amount; user['days'].add(day)
        category = review.get('categories', {}).get(key, row.get('category') or 'Uncategorized')
        if not isinstance(category,str) or not category.strip():
            raise ValueError('category must be nonempty text')
        categories[category] += amount
    if set(review.get('categories', {})) - seen:
        raise ValueError('review categories reference unknown activity IDs')
    total = sum((u['quantity'] for u in users.values()), Decimal(0))
    rows = sorted(users.values(),key=lambda row:(-row['quantity'],row['id']))
    return {'customer_name':review['customer_name'], 'account_id':review['account_id'],
        'prepared_by':review['prepared_by'], 'pilot_start':str(start),'pilot_end':str(end),'data_through':str(through),
        'report_title':cfg['report_title'],'product':policy['company']['product_name'],
        'usage_unit':cfg['usage_unit'],'activity_label':cfg['activity_label'],
        'roster_size':len(users),'active_users':sum(u['records']>0 for u in rows),
        'activity_records':len(seen),'total_quantity':number(total,places),
        'users':[{'id':u['id'],'name':u['name'],'records':u['records'],
                  'quantity':number(u['quantity'],places),'active_days':len(u['days'])} for u in rows],
        'categories':[{'name':key,'quantity':number(value,places)} for key,value in sorted(categories.items())],
        'interpretation':review.get('interpretation',''),
        'limit':'Recorded activity and quantity do not establish completion, value, retention or available balance.'}


def collect(run, review, roster_query, activity_query, policy):
    errors = verify(run)
    if errors:
        raise ValueError('receipt verification failed: ' + '; '.join(errors))
    info = json.loads((run/'run.json').read_text())
    queries, errors = load_queries(run/'calls', stamp(info['started_at']))
    if errors:
        raise ValueError('incomplete source queries: ' + '; '.join(errors))
    by_id = {q['query_id']:q for q in queries}
    roster, activity = by_id.get(roster_query), by_id.get(activity_query)
    if not roster or not activity or roster_query == activity_query:
        raise ValueError('select two distinct complete roster and activity queries')
    exclusive_end = str(date.fromisoformat(review['data_through'])+timedelta(days=1))
    for q, selection in [(roster,'pilot_roster'),(activity,'pilot_activity')]:
        if q.get('source') != 'usage' or q.get('selection') != selection or q.get('account_id') != review['account_id']:
            raise ValueError('usage query account/selection mismatch')
        allowed={'query_id','source','owner_id','selection','account_id','as_of','start_date','end_date','unit','timezone',
                 'records','provider_references','receipt_files','fields','page_size'}
        if set(q)-allowed:
            raise ValueError('unreviewed usage query narrowing')
        if q.get('timezone') != policy['pilot_usage']['timezone']:
            raise ValueError('usage timezone differs from configured contract')
    if roster.get('as_of') != review['data_through']:
        raise ValueError('roster snapshot date mismatch')
    if activity.get('start_date') != review['pilot_start'] or activity.get('end_date') != exclusive_end:
        raise ValueError('usage query window mismatch')
    if activity.get('unit') != policy['pilot_usage']['usage_unit']:
        raise ValueError('usage query unit mismatch')
    return roster['records'], activity['records']


def render(report, policy):
    cfg=policy['pilot_usage'];color=cfg['pdf']['accent_color']
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}',color):
        raise ValueError('PDF accent color must be a hex color')
    e=lambda value:escape(str(value))
    rows=''.join(f'<tr><td>{e(u["name"])}</td><td>{u["records"]}</td><td>{e(u["quantity"])}</td><td>{u["active_days"]}</td></tr>' for u in report['users'])
    cats=''.join(f'<li>{e(c["name"])}: {e(c["quantity"])} {e(report["usage_unit"])}</li>' for c in report['categories'])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(report['report_title'])}</title>
<style>@page{{size:Letter;margin:0.65in}}body{{font:11pt Arial,sans-serif;color:#20272d;line-height:1.45}}h1,h2{{color:{color};break-after:avoid}}.meta{{color:#52606c}}table{{width:100%;border-collapse:collapse;margin:20px 0}}th,td{{text-align:left;border-bottom:1px solid #ccd4da;padding:7px;overflow-wrap:anywhere}}tr{{break-inside:avoid}}.metrics{{padding:16px;background:#edf3f8;font-size:14pt}}.note{{border-left:3px solid {color};padding-left:12px}}footer{{margin-top:28px;font-size:9pt;color:#52606c}}</style></head><body>
<p class="meta">{e(cfg['confidentiality_label'])} · {e(report['product'])}</p><h1>{e(report['report_title'])}</h1><h2>{e(report['customer_name'])}</h2>
<p class="meta">Pilot {e(report['pilot_start'])} to {e(report['pilot_end'])} · Data through {e(report['data_through'])}<br>Prepared by {e(report['prepared_by'])}</p>
<div class="metrics">{report['active_users']} of {report['roster_size']} users active · {report['activity_records']} {e(report['activity_label'])} · {e(report['total_quantity'])} {e(report['usage_unit'])}</div>
<h2>Observed usage</h2><table><thead><tr><th>User</th><th>Records</th><th>{e(report['usage_unit'])}</th><th>Active days</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Usage categories</h2><ul>{cats}</ul><h2>Reviewed interpretation</h2><p>{e(report['interpretation']) or 'No business interpretation supplied.'}</p>
<p class="note">{e(report['limit'])}</p><footer>Scope: the selected account, roster snapshot, date window and normalized unit. Provider permissions and collection limits still apply.</footer></body></html>'''


def run_renderer(command, candidate, timeout):
    """Own an isolated browser until it exits or confirms the PDF write completed."""
    log = candidate.with_suffix('.log')
    complete = False
    with log.open('wb') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=stream, start_new_session=True)
        try:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                detail = log.read_text(errors='replace')
                # Chromium reports this after closing the print output. Some desktop
                # builds keep their browser event loop alive after the print job.
                if candidate.is_file() and re.search(
                    r'\b\d+ bytes written to file ' + re.escape(str(candidate)) + r'(?:\r?\n|$)', detail
                ):
                    complete = True
                    break
                if time.monotonic() >= deadline:
                    raise ValueError('PDF renderer timed out before verified print completion')
                time.sleep(0.1)
            if not complete and (process.returncode != 0 or not candidate.is_file()):
                raise ValueError('PDF renderer failed: ' + log.read_text(errors='replace')[-1000:])
        finally:
            if process.poll() is None:
                try:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait(timeout=5)


def print_pdf(html, output, policy, renderer='auto'):
    from pypdf import PdfReader, PdfWriter
    from pypdf.errors import PdfReadError
    candidates=[renderer] if renderer!='auto' else ['chromium','google-chrome','chromium-browser',
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
      '/Applications/Chromium.app/Contents/MacOS/Chromium']
    binary=next((p for candidate in candidates if (p:=shutil.which(candidate))),None)
    if not binary:raise ValueError('install a Chromium browser or specify --renderer')
    if policy['pilot_usage']['pdf']['page_size']!='Letter':raise ValueError('this PDF renderer supports Letter; adapt CSS before using another size')
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='pilot-pdf-') as tmp:
        candidate=Path(tmp)/'printed.pdf'
        run_renderer([binary,'--headless','--disable-gpu','--no-first-run',
          '--no-default-browser-check','--disable-background-networking','--virtual-time-budget=5000',
          f'--user-data-dir={Path(tmp)/"profile"}',
          '--no-pdf-header-footer',f'--print-to-pdf={candidate}',html.as_uri()],
          candidate,policy['pilot_usage']['pdf']['timeout_seconds'])
        try:
            reader=PdfReader(candidate)
        except PdfReadError as exc:
            raise ValueError('PDF renderer produced an unreadable file') from exc
        if not reader.pages or not any(page.extract_text() for page in reader.pages):raise ValueError('empty PDF')
        for page in reader.pages:
            if abs(float(page.mediabox.width)-612)>1 or abs(float(page.mediabox.height)-792)>1:raise ValueError('unexpected PDF page dimensions')
        writer=PdfWriter();writer.append_pages_from_reader(reader)
        writer.add_metadata({'/Title':policy['pilot_usage']['report_title'],'/Author':policy['pilot_usage']['pdf']['author']})
        verified=Path(tmp)/'verified.pdf'
        with verified.open('wb') as stream:writer.write(stream)
        verified.replace(output)
    return len(reader.pages)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['run','review','roster-query','activity-query','output']:ap.add_argument('--'+name,required=True)
    ap.add_argument('--policy',type=Path,default=ROOT/'_shared/policy.yaml')
    ap.add_argument('--pdf',action='store_true');ap.add_argument('--renderer',default='auto')
    a=ap.parse_args();run=external_path(a.run);output=external_path(a.output)
    if run not in output.parents:raise ValueError('report output must stay within its external run directory')
    policy=yaml.safe_load(a.policy.read_text());review=json.loads(Path(a.review).read_text())
    roster,activity=collect(run,review,a.roster_query,a.activity_query,policy)
    report=compute(review,roster,activity,policy)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    html=output.with_suffix('.html');html.write_text(render(report,policy))
    result={'ready':True,'report':str(output.with_suffix('.json')),'html':str(html)}
    if a.pdf:result.update(pdf=str(output.with_suffix('.pdf')),pages=print_pdf(html,output.with_suffix('.pdf'),policy,a.renderer))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({'ready':False,'error':str(exc)}),file=sys.stderr);raise SystemExit(1)
