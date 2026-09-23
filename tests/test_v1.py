"""V1 release contract, deliberately separate from the extensible YAML schema."""
import ast
import hashlib
import json
import re
import textwrap
import unittest
from pathlib import Path
from tests.content_support import ROOT, MODEL, blocks, fields
from tools import validate

SPEC=ROOT/'v1-content-spec.md'
ROWS=re.findall(r'^\| (\d{2}) \| `([^`]+)` \| [^|]+ \| ([^|]+) \|$',SPEC.read_text(),re.M)
ORDER=[row[1] for row in ROWS]
PREREQS={lid: [ORDER[int(n)-1] for n in re.findall(r'\d{2}',pre)] for _,lid,pre in ROWS}
PRACTICES=['conditions','sets','comprehensions-sort','tests-boundaries']
# Independently reviewed answer anchors (not inferred from the current answer).
ANSWERS=['ba','cb','aa','aa','bb','ba','ba','aa','aa','aa','aa','aa','aa','aa','aa','aa']

class TestV1Release(unittest.TestCase):
    def test_16_published_in_exact_modules_order_and_prerequisites(self):
        self.assertEqual(len(ORDER),16)
        self.assertEqual(MODEL['order'],ORDER)
        self.assertEqual([m['id'] for m in MODEL['modules']],['m1','m2','m3','m4'])
        self.assertEqual([m['lessonIds'] for m in MODEL['modules']],[ORDER[i:i+4] for i in range(0,16,4)])
        self.assertEqual(MODEL['course']['pythonVersion'],'3.13')
        self.assertEqual(MODEL['course']['courseId'],'python-relearn')
        self.assertEqual({p.stem for p in (ROOT/'content/lessons').glob('*.yaml')},set(ORDER))
        for lid in ORDER:
            with self.subTest(lesson=lid):
                l=MODEL['lessons'][lid];self.assertEqual(l['status'],'published');self.assertEqual(l['prerequisites'],PREREQS[lid]);self.assertTrue(6<=len(l['steps'])<=8)

    def test_32_quizzes_and_four_final_practices(self):
        count=0;practices=[]
        for lid,answers in zip(ORDER,ANSWERS):
            steps=MODEL['lessons'][lid]['steps'];quizzes=[s for s in steps if s['type']=='quiz'];count+=len(quizzes)
            with self.subTest(lesson=lid):
                self.assertEqual([q['questionId'] for q in quizzes],[lid+'-q1',lid+'-q2'])
                self.assertEqual(''.join(q['correctOptionId'] for q in quizzes),answers)
                self.assertEqual([s['type'] for s in steps if s['id'] in ['s-goal','s-mechanism','s-predict','s-misconception','s-quiz-1','s-quiz-2','s-recap']],['read','read','reveal','reveal','quiz','quiz','read'])
                if any(s['type']=='practice' for s in steps):
                    practices.append(lid);self.assertEqual(steps[-1]['type'],'practice')
                self.assertIn('口头检查',next(s for s in steps if s['id']=='s-recap')['bodyMd'])
                self.assertIn('独立任务',next(s for s in steps if s['id']=='s-recap')['bodyMd'])
        self.assertEqual(count,32);self.assertEqual(practices,PRACTICES)

    def test_no_early_or_out_of_scope_syntax_in_python_fences(self):
        first={ast.For:5,ast.While:5,ast.List:6,ast.Tuple:6,ast.Dict:7,ast.Set:8,ast.FunctionDef:9,ast.ListComp:12,ast.Try:13,ast.Import:14,ast.ImportFrom:14,ast.With:14,ast.Assert:16}
        forbidden=(ast.Lambda,ast.SetComp,ast.DictComp,ast.GeneratorExp,ast.ClassDef,ast.AsyncFunctionDef,ast.Yield,ast.YieldFrom,ast.Await,ast.NamedExpr,ast.Match)
        methods={'split':6,'append':6,'get':7,'items':7,'add':8,'copy':11,'sort':12,'join':14}
        for num,lid in enumerate(ORDER,1):
            for key,source in blocks(lid).items():
                with self.subTest(lesson=lid,source=key):
                    # The second main fragment continues a function begun in
                    # the preceding block; TestPracticeSource compiles both.
                    if lid=='tests-boundaries' and key=='s-practice/solutionMd/4':continue
                    tree=ast.parse(textwrap.dedent(source))
                    for node in ast.walk(tree):
                        self.assertNotIsInstance(node,forbidden)
                        for kind,minimum in first.items():
                            if isinstance(node,kind):self.assertGreaterEqual(num,minimum,ast.dump(node))
                        if isinstance(node,ast.Attribute):
                            self.assertNotIn(node.attr,('pop','values','write_bytes','__name__'))
                            if node.attr in methods:self.assertGreaterEqual(num,methods[node.attr])
                        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='sorted':self.assertGreaterEqual(num,12)
                        if isinstance(node,(ast.Import,ast.ImportFrom)):
                            names=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names]
                            self.assertTrue(set(names)<= {'pathlib','sys','word_tools'},names)
                        if isinstance(node,ast.ListComp):self.assertEqual(len(node.generators),1);self.assertLessEqual(len(node.generators[0].ifs),1)

    def test_independent_editorial_review_has_not_gone_stale(self):
        seal=json.loads((ROOT/'docs/v1-review.json').read_text())
        reviewed={'python_relearn_kindle_v1_spec.md','v1-content-spec.md','content/course.yaml'}
        reviewed.update('content/lessons/'+lid+'.yaml' for lid in ORDER)
        self.assertEqual(set(seal['sha256']),reviewed)
        for rel,digest in seal['sha256'].items():
            with self.subTest(file=rel):self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest,'内容/规格变更后须重新人工审核并更新审阅记录，不能自动重算签名冒充审核')
        self.assertEqual(set(seal['lessons']),set(ORDER))

class TestAdditionalValidation(unittest.TestCase):
    def test_duplicate_yaml_keys_are_errors(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.yaml';path.write_text('revision: 1\nrevision: 2\n');errors=[]
            self.assertIsNone(validate.load_yaml(path,errors));self.assertIn('重复',str(errors));self.assertIn('bad.yaml',str(errors))
    def test_invalid_revision_and_boolean_schema(self):
        from tests.test_validate import write_set,make_lesson
        import tempfile
        for changes in [{'revision':0},{'revision':-1},{'schemaVersion':True},{'prerequisites':7}]:
            with self.subTest(changes=changes),tempfile.TemporaryDirectory() as tmp:
                content,config,course=write_set(tmp,{'one':make_lesson('one',**changes)})
                self.assertTrue(validate.validate_all(content,config,course))
    def test_published_cannot_depend_on_draft(self):
        from tests.test_validate import write_set,make_lesson
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            content,config,course=write_set(tmp,{'one':make_lesson('one',status='draft'),'two':make_lesson('two',prerequisites=['one'])})
            self.assertIn('draft',' '.join(validate.validate_all(content,config,course)))
