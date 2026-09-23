"""Blueprint P1-P4: run YAML solutions with independent full-output oracles."""
import ast
import contextlib
import copy
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tests.content_support import part, solution, ROOT

P1_INPUT='raw_title = " Python Basics "\nraw_count = "3"\nunit_price = 20\nis_member = False\n'
P1_OUTPUT='资料：python basics\n份数：3\n应付：68.00 元\n'
P2_OUTPUT='有效记录：6\n不同标签：3\n忽略记录：2\npython: 2\nsql: 2\napi: 2\n'
P3_OUTPUT='有效记录：5\ncli: 0\npython: 15\nsql: 20\napi: 20\npython: 30\n'
P4_INPUT='Python python\nSQL api SQL\n\nAPI python\n'
P4_OUTPUT='总词数：7\n不同词数：3\npython: 3\nsql: 2\napi: 2\n'

def execute(code, overrides=None):
    tree=ast.parse(code)
    if overrides:
        for node in tree.body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in overrides:
                node.value=ast.parse(repr(overrides[node.targets[0].id]),mode='eval').body
    scope={};buf=io.StringIO()
    with contextlib.redirect_stdout(buf): exec(compile(ast.fix_missing_locations(tree),'<textbook>','exec'),scope)
    return scope,buf.getvalue()

def practice_files():
    return {
      'word_tools.py':'\n'.join(part('tests-boundaries','s-practice','solutionMd',i) for i in range(3)),
      'main.py':'\n'.join(part('tests-boundaries','s-practice','solutionMd',i) for i in (3,4)),
      'check_examples.py':part('tests-boundaries','s-practice','solutionMd',5),
    }

class TestPracticeSource(unittest.TestCase):
    def test_p1_all_seven_contract_cases(self):
        inputs=[({},P1_OUTPUT),({'raw_count':'4'},P1_OUTPUT.replace('份数：3','份数：4').replace('68.00','88.00')),({'raw_count':'5'},P1_OUTPUT.replace('份数：3','份数：5').replace('68.00','100.00')),({'is_member':True},P1_OUTPUT.replace('68.00','60.00')),({'raw_count':'0'},P1_OUTPUT.replace('份数：3','份数：0').replace('68.00','0.00')),({'raw_count':'-1'},'输入无效\n'),({'raw_title':'   '},'输入无效\n')]
        for changes,want in inputs:
            with self.subTest(changes=changes):self.assertEqual(execute(P1_INPUT+solution('conditions'),changes)[1],want)
        self.assertEqual(execute(P1_INPUT+solution('conditions'),{'raw_count':'0','is_member':True})[1],P1_OUTPUT.replace('份数：3','份数：0').replace('68.00','0.00'))

    def test_p2_all_five_contract_cases_full_text(self):
        cases=[(None,P2_OUTPUT),([], '有效记录：0\n不同标签：0\n忽略记录：0\n'),(['','   '],'有效记录：0\n不同标签：0\n忽略记录：2\n'),(['API',' api ','api'],'有效记录：3\n不同标签：1\n忽略记录：0\napi: 3\n'),(['SQL','Python'],'有效记录：2\n不同标签：2\n忽略记录：0\nsql: 1\npython: 1\n')]
        for data,want in cases:
            with self.subTest(data=data):self.assertEqual(execute(solution('sets'),{'raw_tags':data} if data is not None else None)[1],want)

    def test_p3_all_seven_contract_cases_and_one_call_per_record(self):
        scope,out=execute(solution('comprehensions-sort'));self.assertEqual(out,P3_OUTPUT)
        clean=scope['clean_records'];original=copy.deepcopy(scope['records'])
        self.assertEqual(clean([]),[])
        self.assertEqual(clean([{'name':'CLI','minutes':0}]),[{'name':'cli','minutes':0}])
        self.assertEqual(clean([{'name':' ','minutes':1},{'name':'X','minutes':-1}]),[])
        first=clean(scope['records']);second=clean(scope['records']);self.assertEqual(first,second)
        first[0]['name']='changed';self.assertEqual(scope['records'],original);self.assertNotEqual(first,second)
        calls=[];real=scope['clean_record']
        def counted(record):calls.append(record);return real(record)
        scope['clean_record']=counted;clean(scope['records']);self.assertEqual(len(calls),len(original))
        self.assertEqual(execute(solution('comprehensions-sort'),{'records':[]})[1],'有效记录：0\n')

    def test_p4_all_content_cases_complete_report_and_no_mutation(self):
        scope,out=execute(practice_files()['word_tools.py']);self.assertEqual(out,'')
        count=scope['count_words'];report=scope['format_report']
        cases=[(P4_INPUT,{'python':3,'sql':2,'api':2},P4_OUTPUT),('',{},'总词数：0\n不同词数：0\n'),(' \n\t ',{},'总词数：0\n不同词数：0\n'),('Python',{'python':1},'总词数：1\n不同词数：1\npython: 1\n'),('API api API',{'api':3},'总词数：3\n不同词数：1\napi: 3\n'),('sql api',{'sql':1,'api':1},'总词数：2\n不同词数：2\nsql: 1\napi: 1\n'),('数据 data 数据',{'数据':2,'data':1},'总词数：3\n不同词数：2\n数据: 2\ndata: 1\n'),('Python, python',{'python,':1,'python':1},'总词数：2\n不同词数：2\npython,: 1\npython: 1\n')]
        for text,counts,want in cases:
            with self.subTest(text=text):
                actual=count(text);self.assertEqual(actual,counts);self.assertEqual(count(text),counts)
                before=list(actual.items());self.assertEqual(report(actual),want);self.assertEqual(list(actual.items()),before)

    def test_p4_real_module_import_entrypoint_and_file_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,text in practice_files().items():(root/name).write_text(text,encoding='utf-8')
            def run(*args):return subprocess.run([sys.executable,'-B',*args],cwd=root,capture_output=True,timeout=10)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            p=run('-c','import word_tools; import main');self.assertEqual((p.returncode,p.stdout,p.stderr),(0,b'',b''));self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
            p=run('check_examples.py');self.assertEqual(p.returncode,0,p.stderr)
            src=root/'input.txt';out=root/'report.txt'
            for i in range(2):
                src.write_text(P4_INPUT,encoding='utf-8');p=run('main.py');self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(out.read_bytes(),P4_OUTPUT.encode())
            for mode in ['missing','bad-utf8','read-oserror']:
                if src.exists():src.unlink()
                if mode=='bad-utf8':src.write_bytes((ROOT/'content/samples/invalid-utf8.txt').read_bytes())
                if mode=='read-oserror':src.mkdir()
                p=run('main.py');self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('报告已生成',p.stdout.decode());self.assertEqual(out.read_bytes(),P4_OUTPUT.encode())
                self.assertIn({'missing':'不存在','bad-utf8':'UTF-8','read-oserror':'读取输入文件失败'}[mode],p.stdout.decode())
                if src.is_dir():src.rmdir()
            src.write_text(P4_INPUT,encoding='utf-8');out.unlink();out.mkdir();p=run('main.py');self.assertIn('写入报告失败',p.stdout.decode());self.assertNotIn('报告已生成',p.stdout.decode());out.rmdir()
            out.write_text('旧报告',encoding='utf-8')
            p=run('-c','import main\ndef broken(text):\n    return nonexistent\nmain.count_words=broken\nmain.main()');self.assertNotEqual(p.returncode,0);self.assertIn(b'NameError',p.stderr);self.assertEqual(out.read_text(),'旧报告')

    def test_reference_fixture_solutions_match_textbook_ast(self):
        pairs=[('conditions/p1_solution.py',P1_INPUT+solution('conditions')),('sets/practice.py',solution('sets')),('comprehensions-sort/solution.py',solution('comprehensions-sort')),('tests-boundaries/reference_solution.py',practice_files()['word_tools.py'])]
        def canonical(source):
            tree=ast.parse(source)
            tree.body=[n for n in tree.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))]
            return ast.dump(tree,include_attributes=False)
        for rel,source in pairs:
            with self.subTest(fixture=rel):self.assertEqual(canonical((ROOT/'content/fixtures'/rel).read_text()),canonical(source))
