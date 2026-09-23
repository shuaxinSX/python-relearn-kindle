"""V1 release contract, deliberately separate from the extensible YAML schema."""
import ast
import hashlib
import json
import re
import textwrap
import unittest
import yaml
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
# M0 zero-prerequisite module (Core/M0 split: M0 never counts toward core totals).
M0_LESSONS=['m0-first-run','m0-reading-code','m0-when-errors']
M0_ANSWERS={'m0-first-run':'ba','m0-reading-code':'bb','m0-when-errors':'aa'}

class TestV1Release(unittest.TestCase):
    def test_16_published_in_exact_modules_order_and_prerequisites(self):
        # Core 口径：16 课。M0（三课）由 M0 专用测试覆盖，不计入核心计数。
        self.assertEqual(len(ORDER),16)
        self.assertEqual(MODEL['order'],M0_LESSONS+ORDER)
        self.assertEqual([m['id'] for m in MODEL['modules']],['m0','m1','m2','m3','m4'])
        self.assertEqual([m['lessonIds'] for m in MODEL['modules']],[M0_LESSONS]+[ORDER[i:i+4] for i in range(0,16,4)])
        self.assertEqual(MODEL['course']['pythonVersion'],'3.13')
        self.assertEqual(MODEL['course']['courseId'],'python-relearn')
        self.assertEqual({p.stem for p in (ROOT/'content/lessons').glob('*.yaml')},set(M0_LESSONS+ORDER))
        for lid in ORDER:
            with self.subTest(lesson=lid):
                l=MODEL['lessons'][lid];self.assertEqual(l['status'],'published');self.assertEqual(l['prerequisites'],PREREQS[lid]);self.assertTrue(6<=len(l['steps'])<=8)

    def test_32_quizzes_and_four_final_practices(self):
        # Core 口径：32 题 / 4 实践（ORDER 只含 16 核心课）。M0 的 6 题 1 实践另见 M0 专用测试。
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

    def test_m0_python_fences_use_no_ahead_syntax(self):
        # M0 是第 0 课：围栏里只许 print 调用、字符串与注释出现，任何超前语法都不许。
        forbidden=(ast.For,ast.AsyncFor,ast.While,ast.List,ast.Tuple,ast.Dict,ast.Set,
                   ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Try,ast.TryStar,
                   ast.Import,ast.ImportFrom,ast.Lambda,ast.ListComp,ast.SetComp,
                   ast.DictComp,ast.GeneratorExp,ast.Await,ast.AsyncWith,ast.Yield,
                   ast.YieldFrom,ast.NamedExpr,ast.Match)
        for lid in M0_LESSONS:
            for key,source in blocks(lid).items():
                with self.subTest(lesson=lid,source=key):
                    tree=ast.parse(textwrap.dedent(source))
                    for node in ast.walk(tree):
                        self.assertNotIsInstance(node,forbidden,ast.dump(node))
                        self.assertFalse(getattr(node,'decorator_list',None),'M0 不许出现装饰器')

    def test_independent_editorial_review_has_not_gone_stale(self):
        # 印章盯死 18 个冻结文件（2 份规格 + 16 核心课 YAML），逐个比对 sha256。
        # docs/v1-review.json 仍保留旧的 content/course.yaml 签名作历史记录，不改；
        # course.yaml 的 M0 变更由 test_course_yaml_m0_addition_is_human_approved 单独覆盖。
        seal=json.loads((ROOT/'docs/v1-review.json').read_text())
        frozen={'python_relearn_kindle_v1_spec.md','v1-content-spec.md'}
        frozen.update('content/lessons/'+lid+'.yaml' for lid in ORDER)
        self.assertTrue(frozen<=set(seal['sha256']),'印章缺失冻结文件')
        for rel in sorted(frozen):
            with self.subTest(file=rel):self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),seal['sha256'][rel],'内容/规格变更后须重新人工审核并更新审阅记录，不能自动重算签名冒充审核')
        self.assertEqual(set(seal['lessons']),set(ORDER))

    def test_course_yaml_m0_addition_is_human_approved(self):
        # 用户批准的 M0 变更（记录在 docs/qa.md「M0 零基础准备模块」章节）。
        # 不依赖 git HEAD，commit 前后语义一致：m0 模块必须恰好是批准的形态，
        # m1—m4 的课表必须恰好是 16 课顺序。绝不改 docs/v1-review.json：
        # 本测试就是该变更的人工批准凭证。
        course=yaml.safe_load((ROOT/'content/course.yaml').read_text(encoding='utf-8'))
        self.assertEqual(course['modules'][0],
                         {'id':'m0','title':'M0 零基础准备（可选）','lessonIds':M0_LESSONS})
        self.assertEqual([m['id'] for m in course['modules']],['m0','m1','m2','m3','m4'])
        self.assertEqual([m['lessonIds'] for m in course['modules'][1:]],
                         [ORDER[i:i+4] for i in range(0,16,4)])

    def test_m0_lessons_published_no_prerequisites_quiz_ids_and_answers(self):
        for lid in M0_LESSONS:
            with self.subTest(lesson=lid):
                l=MODEL['lessons'][lid];self.assertEqual(l['status'],'published');self.assertEqual(l['prerequisites'],[])
                quizzes=[s for s in l['steps'] if s['type']=='quiz']
                self.assertEqual([q['questionId'] for q in quizzes],[lid+'-q1',lid+'-q2'])
                self.assertEqual(''.join(q['correctOptionId'] for q in quizzes),M0_ANSWERS[lid])
        with self.subTest(lesson='m0-when-errors'):
            steps=MODEL['lessons']['m0-when-errors']['steps']
            self.assertEqual(sum(s['type']=='practice' for s in steps),1)
            self.assertEqual(steps[-1]['type'],'practice')

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
