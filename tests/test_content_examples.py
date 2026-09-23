"""Execute every Python fence from the real textbook, with explicit context/oracles.

No generated 'actual == actual' expected values. Long practices are assembled by
stage; the deliberately infinite while prompt is tested after its stated repair.
Environment-dependent paths are asserted as paths, never a fixed local string.
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from tests.content_support import MODEL, blocks, part, solution

# Exact source locators -> execution requirements. Values are independently
# worked out from the blueprint; wrong choices are executed too where finite.
CASES={}
def case(lid,key,stdout='',setup='',check='',exception=None,files=None,replace=None):
    CASES[(lid,key)]={'stdout':stdout,'setup':setup,'check':check,'exception':exception,'files':files or {},'replace':replace}
def body(lid,step,out='',**kw):case(lid,step+'/bodyMd/0',out,**kw)
def prompt(lid,n,out='',**kw):case(lid,f's-quiz-{n}/promptMd/0',out,**kw)
def option(lid,n,opt,out='',**kw):case(lid,f's-quiz-{n}/options/{opt}/textMd/0',out,**kw)

lid='run-and-bindings'
body(lid,'s-mechanism','2 3\n');body(lid,'s-predict','python basics\n2 3\n');prompt(lid,1,'2 3\n');prompt(lid,2,check='assert price == 20 and copies == 2')
for opt,value in [('a',60),('b',40),('c',40),('d',60)]:option(lid,2,opt,setup=part(lid,'s-quiz-2','promptMd'),check=f'assert total == {value}')
lid='types-and-none'
body(lid,'s-mechanism',"3 3\n<class 'str'> <class 'int'>\n");body(lid,'s-predict','32\n5\n');body(lid,'s-misconception',"3\n3\n<class 'str'>\n");prompt(lid,1,check='assert type(raw) is str and type(count) is int and count+2 == 5')
lid='strings'
body(lid,'s-mechanism','10\nreport\ntxt\nreport.txt\n应付：68.00 元\n');body(lid,'s-predict','report.txt\n Report.TXT \n');body(lid,'s-misconception',' Report.TXT \n');prompt(lid,1,check='assert name[0:6] == "report" and name[-3:] == "txt"');prompt(lid,2,check='assert raw == " Report.TXT "')
for opt,clean,raw in [('a','report.txt',' Report.TXT '),('b',' Report.TXT ',' Report.TXT '),('c',' report.txt ',' Report.TXT '),('d','report.txt','report.txt')]:option(lid,2,opt,setup='raw=" Report.TXT "',check=f'assert (clean,raw) == {(clean,raw)!r}')
lid='conditions'
body(lid,'s-mechanism','优惠\n');body(lid,'s-predict','免服务费\n');body(lid,'s-misconception','免服务费\n优惠\n');prompt(lid,1,'免服务费\n')
for opt,out in [('a','未填写\n'),('b','未填写\n'),('c','')]:option(lid,2,opt,out,setup='count=None')
lid='loops'
body(lid,'s-mechanism','3\n');body(lid,'s-predict','3\n');body(lid,'s-misconception','3\n2\n1\ndone\n');prompt(lid,1,'6\n')
prompt(lid,2,'3\n2\n1\n',replace=('    print(remaining)','    print(remaining)\n    remaining = remaining - 1'))
lid='lists-tuples'
body(lid,'s-mechanism',"['python', 'api']\npython 30\n['INFO', 'ERROR', 'INFO']\n");body(lid,'s-predict',"['info', 'error']\n");body(lid,'s-misconception',"['python', 'api']\nNone\n");prompt(lid,1,'sql\npython\nsql\n');prompt(lid,2,check='assert items == ["python","api"] and result is None')
lid='dicts'
body(lid,'s-mechanism','python\n0\nFalse\nname python\nminutes 30\n');body(lid,'s-predict',"{'python': 2, 'sql': 1}\n");body(lid,'s-misconception','{}\n');prompt(lid,1,'0\nFalse\n');prompt(lid,2,"{'python': 1, 'sql': 1}\n")
for opt,val in [('a',1),('b',1),('d',None)]:option(lid,2,opt,setup='counts={}\ntag="python"',check=f'assert counts == '+ ('{}' if val is None else '{"python":1}'))
option(lid,2,'c',setup='counts={}\ntag="python"',exception='KeyError')
lid='sets'
body(lid,'s-mechanism','2\nTrue\n');body(lid,'s-predict',"['python', 'sql']\n2\n");body(lid,'s-misconception','2\n');prompt(lid,1,'2\nTrue\n')
for opt,check in [('a','assert unique == ["python","sql"] and counts == {"python":2,"sql":1}'),('b','assert counts == {"python":1,"sql":1}'),('c','assert type(unique) is set and counts == {"python":2,"sql":1}'),('d','assert unique == ["python","sql"] and counts == {"python":1,"sql":1}')]:option(lid,2,opt,check=check)
case(lid,'s-practice/taskMd/0',check='assert len(raw_tags) == 8')
lid='functions'
body(lid,'s-mechanism',check='assert clean_names([" A ","B"]) == ["a","b"] and clean_names([]) == []');body(lid,'s-predict','python\napi\n');body(lid,'s-misconception','python\nsql\nNone\n');prompt(lid,1,'SQL\nNone\n');prompt(lid,2,"['a']\nNone\n")
for opt,value in [('a',['a','b']),('b',[]),('c',None),('d',['a'])]:option(lid,2,opt,check=f'assert clean_names([" A ","B"]) == {value!r}')
lid='scope-defaults'
body(lid,'s-mechanism','5\n9\n');body(lid,'s-predict','3\n10\n');body(lid,'s-misconception',"['sql']\n['sql', 'api']\n");prompt(lid,1,'3\n10\n');prompt(lid,2,"['sql']\n['sql', 'api']\n")
for opt in ['a','b','d']:option(lid,2,opt,check='assert add_tag("sql") == ["sql"]\nassert add_tag("api") == ["api"]\nb=[]\nr=add_tag("x",b)\nassert (r is b) == '+str(opt=='a'))
option(lid,2,'c',check='assert add_tag("sql") == {"sql":True}\nassert add_tag("api") == {"sql":True,"api":True}')
lid='alias-copy'
body(lid,'s-mechanism','45 sql\n');body(lid,'s-predict','45\n45\n');body(lid,'s-misconception','python\nsql\n');body(lid,'s-copy','[[1, 9], [2]]\nFalse\n');prompt(lid,1,check='assert a is b and a == ["sql","api"]');prompt(lid,2,check='assert a == [[1,9],[2]] and a is not b')
lid='comprehensions-sort'
body(lid,'s-mechanism',check='assert [r["name"] for r in ordered] == ["b","a"]');body(lid,'s-predict',"['a', 'b'] ['a', 'b']\n");body(lid,'s-misconception',"['b', 'a']\n['a', 'b']\nNone\n");prompt(lid,1,check='assert result == ["a","b"]');prompt(lid,2,check='assert [r["name"] for r in ordered] == ["b","c","a"]\nassert [r["name"] for r in records] == ["a","b","c"]')
for opt,expected in [('a',['a','b']),('b',['']),('c',['a','','b']),('d',[' A ','B'])]:option(lid,1,opt,setup='raw=[" A ","","B"]',check=f'assert cleaned == {expected!r}')
case(lid,'s-practice/taskMd/0',check='assert len(records) == 7 and records[5] == {"name":"CLI","minutes":0}')
lid='exceptions'
body(lid,'s-predict','ValueError\n');body(lid,'s-misconception','[0]\n');prompt(lid,1,exception='ValueError')
for opt,values in [('a',[0,5]),('b',[0,0,5]),('c',[0]),('d',[5])]:option(lid,2,opt,check=f'assert results == {values!r}'+ ('\nassert bad_items == ["bad"]' if opt=='a' else ''))
lid='paths-text'
body(lid,'s-mechanism','False\ninput.txt\n');body(lid,'s-join','总词数：4\npython: 2\n');body(lid,'s-predict','4\n2\n',files={'input.txt':'Python python\nSQL api\n'})
body(lid,'s-misconception','读取失败\n旧报告还在： False\n',files={'report.txt':'旧报告'},check='assert Path("report.txt").read_bytes() == b""')
option(lid,2,'a',setup='from pathlib import Path',files={'input.txt':'Python python\nSQL api\n','report.txt':'旧报告'},check='assert Path("report.txt").read_text() == "词数：4\\n"')
option(lid,2,'b',setup='from pathlib import Path',files={'report.txt':'旧报告'},exception='FileNotFoundError')
lid='modules-venv'
# Capture sys.executable without treating a machine-specific path as a fixed answer.
body(lid,'s-mechanism',setup='import contextlib,io\n_capture=io.StringIO()\n_cm=contextlib.redirect_stdout(_capture)\n_cm.__enter__()',check='_cm.__exit__(None,None,None)\nassert _capture.getvalue().strip() == sys.executable')
body(lid,'s-predict','loaded\nreport\n')
case(lid,'s-predict/bodyMd/1',"loaded\n{'sql': 2}\n",files={'word_tools.py':part(lid,'s-predict')})
body(lid,'s-misconception','loaded\nreport\n')
prompt(lid,1,'loaded\n',setup='__name__="word_tools"')
lid='tests-boundaries'
body(lid,'s-mechanism','AssertionError\ndone\n');body(lid,'s-predict','ok\n');body(lid,'s-misconception',"[]\n['A']\n");prompt(lid,1,check='assert keep_names([{"name":"CLI","minutes":0}]) == []')
for opt in 'abcd':option(lid,1,opt,setup=part(lid,'s-quiz-1','promptMd'),exception='AssertionError' if opt in 'ad' else None)
for opt in 'abcd':option(lid,2,opt,"{'python': 2}\n" if opt=='b' else '',setup=part(lid,'s-practice','solutionMd',0))

# M0: 13 个 Python 围栏全部显式执行归属与独立预期（practice 的两块也直接可运行）。
lid='m0-first-run'
body(lid,'s-first-code','Hello\n')
case(lid,'s-first-code/bodyMd/1','Hello, 世界\n')
body(lid,'s-two-lines','你好\n早上好\n')
body(lid,'s-rerun','再见\n')
lid='m0-reading-code'
body(lid,'s-lines','你好\n世界\n')
body(lid,'s-symbols','你好 世界\n')
body(lid,'s-comment','你好\n')
body(lid,'s-space','你好   世界\n')
lid='m0-when-errors'
case(lid,'s-example-quote/revealMd/0','你好\nhello\n')
case(lid,'s-example-name/revealMd/0','早安\nhello\n')
case(lid,'s-recap/bodyMd/0','小明\n我正在重新学习 Python\n')
case(lid,'s-practice/solutionMd/0','小明\n我正在重新学习 Python\n')
case(lid,'s-practice/solutionMd/1','小小明\n我正在重新学习 Python\n')

# These fragments are consumed verbatim in TestPracticeSource below, including
# their indentation and file imports. They are never silently skipped.
PRACTICE_BLOCKS={(lid,key) for lid in MODEL['order'] for key in blocks(lid) if key.startswith('s-practice/solutionMd/')}

class TestTextbookFences(unittest.TestCase):
    def test_inventory_has_explicit_execution_for_every_python_fence(self):
        actual={(lid,key) for lid in MODEL['order'] for key in blocks(lid)}
        self.assertEqual(actual,set(CASES)|PRACTICE_BLOCKS)

    def test_source_fences_outputs_and_assertions(self):
        for (lid,key),case in CASES.items():
            with self.subTest(lesson=lid,source=key),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name,data in case['files'].items(): (root/name).write_text(data,encoding='utf-8')
                source=blocks(lid)[key]
                if case['replace']:
                    old,new=case['replace'];self.assertIn(old,source);source=source.replace(old,new)
                script=root/'example.py'
                script.write_text(case['setup']+'\n'+source+'\n'+case['check']+'\n',encoding='utf-8')
                proc=subprocess.run([sys.executable,'-B',str(script)],cwd=root,capture_output=True,timeout=5,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
                self.assertEqual(proc.stdout,case['stdout'].encode('utf-8'))
                if case['exception']:
                    self.assertNotEqual(proc.returncode,0)
                    self.assertRegex(proc.stderr.decode(),r'(?m)^'+case['exception']+r'(?::|$)')
                else:
                    self.assertEqual(proc.returncode,0,proc.stderr.decode())
                    self.assertEqual(proc.stderr,b'')
