"""A1-A11: Chromium HTTP regression, mandatory for final audit (no silent skip)."""
import contextlib
import functools
import http.server
import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from tools import build

ROOT=Path(__file__).resolve().parents[1]
BROWSER_REPORTS=[]
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class TestBrowser(unittest.TestCase):
    def test_deployment_checker_rejects_stale_and_missing_artifacts(self):
        from tools.audit_v1 import check_deployment
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);local=root/'local';remote=root/'remote'
            local.mkdir();remote.mkdir()
            for directory in (local,remote):
                (directory/'index.html').write_text('<h1>V1</h1>')
                (directory/'reader.js').write_text('var v1 = true;')
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(remote)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}/'
                self.assertEqual(check_deployment(local,url)['status'],'pass')
                (remote/'reader.js').write_text('var old = true;')
                self.assertEqual(check_deployment(local,url)['status'],'fail')
                (remote/'reader.js').unlink()
                self.assertEqual(check_deployment(local,url)['status'],'fail')
            finally:
                server.shutdown();server.server_close();thread.join()

    def test_http_browser_regressions_both_base_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for base in ('/', '/python-relearn-kindle/'):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(build.main(['--out',str(root/base.strip('/')), '--base-path',base]),0)
                server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    proc=subprocess.run(['node',str(ROOT/'tests/browser_driver.js'),f'http://127.0.0.1:{server.server_port}{base}'],capture_output=True,text=True,timeout=180)
                    self.assertEqual(proc.returncode,0,proc.stderr)
                    results=json.loads(proc.stdout)
                    BROWSER_REPORTS.append({'basePath':base, 'cases':results})
                    self.assertGreaterEqual(len(results),1 if os.environ.get("PRL_BROWSER_FILTER") else 20,proc.stderr)
                    for r in results:
                        with self.subTest(base=base,case=r['name']):
                            self.assertTrue(r['pass'],r.get('error'))
                finally:
                    server.shutdown();server.server_close();thread.join()
