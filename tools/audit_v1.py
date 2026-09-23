#!/usr/bin/env python3
"""Single V1 acceptance gate. Uses the existing validator, unittest suite and builder.

Requires Python 3.13, locked Python/Node dev dependencies and Playwright Chromium.
Optional --deployed-url also byte-compares every generated artifact with Pages.
A successful local audit is not a claim of deployment or Kindle device acceptance.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from urllib.parse import urlsplit, quote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def check_deployment(dist:Path, url:str):
    """Network opt-in. A stale deployment is an error, not a warning."""
    errors=[];checked=[]
    for file in sorted(p for p in dist.rglob('*') if p.is_file()):
        rel=file.relative_to(dist).as_posix()
        try:
            req=urllib.request.Request(url.rstrip('/')+'/'+quote(rel),headers={'Cache-Control':'no-cache','User-Agent':'python-relearn-v1-audit'})
            with urllib.request.urlopen(req,timeout=20) as response:
                payload=response.read()
                if response.status!=200 or payload!=file.read_bytes():errors.append(f'{rel}: deployed bytes differ (stale or wrong deployment)')
                checked.append({'file':rel,'status':response.status,'sha256':hashlib.sha256(payload).hexdigest()})
        except (OSError,urllib.error.URLError) as exc:errors.append(f'{rel}: {exc}')
    return {'url':url,'checked':checked,'errors':errors,'status':'fail' if errors else 'pass'}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-path',default='/python-relearn-kindle/')
    parser.add_argument('--out',default='dist')
    parser.add_argument('--report',default='audit-results/v1-audit.json')
    parser.add_argument('--deployed-url',help='Opt in to checking the actual Pages artifact against this checkout')
    args=parser.parse_args(argv)
    started=time.monotonic();os.chdir(ROOT)
    report={'schemaVersion':1,'python':sys.version.split()[0],'checks':{},'errors':[],
            'manual':['Kindle Scribe: model/firmware/network/date; touch, fonts, code scroll, sleep/wake, reopen, backup restore',
                      'Editorial meaning is independently reviewed and SHA-pinned; future edits need human re-review.']}
    def finish():
        report['elapsedSeconds']=round(time.monotonic()-started,2)
        report['status']='fail' if report['errors'] else 'pass'
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"V1 AUDIT {report['status'].upper()} — {path}")
        for error in report['errors']:print('ERROR:',error)
        print('Kindle 实机：待验；本地 PASS 不代表线上已更新。')
        return 1 if report['errors'] else 0
    if sys.version_info[:2]!=(3,13):report['errors'].append('Python 3.13 is required; other versions cannot certify the declared baseline')
    if not shutil.which('node'):report['errors'].append('Node is required; runtime tests may not be silently skipped')
    if os.environ.get('PYTHONOPTIMIZE') or not __debug__:report['errors'].append('Optimized Python disables fixture assertions; remove PYTHONOPTIMIZE/-O')
    if os.environ.get('PRL_BROWSER_FILTER'):report['errors'].append('PRL_BROWSER_FILTER must be unset for a full audit')
    if report['errors']:return finish()
    try:
        from tools import validate,build
    except ImportError as exc:
        report['errors'].append(f'Install requirements-build.txt first: {exc}');return finish()
    preflight=subprocess.run(['node','-e',"require('acorn');const p=require('playwright');if(!require('fs').existsSync(p.chromium.executablePath()))process.exit(1)"],capture_output=True,text=True)
    if preflight.returncode:
        report['errors'].append('Install dev tools: npm ci && npx playwright install chromium');return finish()
    errors=validate.validate_all(ROOT/'content',ROOT/'config.yaml',ROOT/'content/course.yaml')
    report['checks']['schema']={'errors':errors};report['errors'].extend(errors)
    if errors:return finish()
    from tests.content_support import MODEL,blocks
    from tests.test_examples import iter_scripts
    lessons=[MODEL['lessons'][lid] for lid in MODEL['order']]
    report['inventory']={'lessons':len(lessons),'published':sum(l['status']=='published' for l in lessons),
       'quizzes':sum(s['type']=='quiz' for l in lessons for s in l['steps']),
       'practices':sum(s['type']=='practice' for l in lessons for s in l['steps']),
       'fixtures':len(list(iter_scripts())), 'pythonFences':sum(len(blocks(l['id'])) for l in lessons)}
    print('Inventory:',json.dumps(report['inventory'],ensure_ascii=False),flush=True)
    # Exactly the normal unittest suite. Fixtures and browser cases live there.
    log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    logpath=Path(args.report).with_suffix('.tests.log');logpath.parent.mkdir(parents=True,exist_ok=True);logpath.write_text(log.getvalue())
    report['checks']['tests']={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'log':str(logpath)}
    from tests.test_browser import BROWSER_REPORTS
    report['checks']['browser']=BROWSER_REPORTS
    if not result.wasSuccessful() or result.skipped or result.testsRun < 70:report['errors'].append(f'Tests must all pass with zero skips; see {logpath}')
    print('Tests:',report['checks']['tests'],flush=True)
    # root/subpath browser tests already build both paths; leave a production build.
    rc=build.main(['--base-path',args.base_path,'--out',args.out])
    report['checks']['build']={'returncode':rc,'basePath':args.base_path}
    if rc:report['errors'].append('Production build failed')
    else:
        dist=Path(args.out)
        report['artifacts']={p.relative_to(dist).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dist.rglob('*')) if p.is_file()}
        if args.deployed_url:
            if urlsplit(args.deployed_url).path.rstrip('/')+'/' != args.base_path:
                report['errors'].append('--base-path must match the deployment URL path')
            else:
                deployment=check_deployment(dist,args.deployed_url);report['checks']['deployment']=deployment;report['errors'].extend(deployment['errors'])
        else:report['checks']['deployment']={'status':'not-checked','reason':'Use --deployed-url after deployment; workflow/path gates covered locally'}
    report['source']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'python_relearn_kindle_v1_spec.md',ROOT/'v1-content-spec.md']}
    report['gitHead']=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
    report['workingTreeDirty']=bool(subprocess.run(['git','status','--porcelain'],capture_output=True,text=True).stdout)
    return finish()

if __name__=='__main__':raise SystemExit(main())
