"""M0 zero-prerequisite module: content-quality contract (Core/M0 split).

M0 is lesson 0. Its prose and code fences must not assume knowledge taught
in M1-M4; its quizzes probe observable operations (predict output, locate
the error), not terminology; its practice walks 7 explicit sub-steps.
"""
import re
import unittest
from tests.content_support import MODEL, blocks

M0=['m0-first-run','m0-reading-code','m0-when-errors']
# 英文标识符级超纲词：词边界匹配，大小写不敏感。
BANNED_WORDS=['list','dict','set','tuple','def','class','try','except','import',
              'lambda','for','while','return','yield','await','async','global',
              'nonlocal','del','raise','assert','with','comprehension']
# 中文超纲概念词。
BANNED_ZH=['列表','元组','字典','函数','循环','导入','异常','变量','参数','对象']

def md_text(lid):
    parts=[]
    for step in MODEL['lessons'][lid]['steps']:
        for key,value in step.items():
            if key.endswith('Md') and isinstance(value,str):parts.append(value)
        for opt in step.get('options',[]):
            for key,value in opt.items():
                if key.endswith('Md') and isinstance(value,str):parts.append(value)
    return '\n'.join(parts)

def quizzes(lid):
    return [s for s in MODEL['lessons'][lid]['steps'] if s['type']=='quiz']

class TestM0ContentQuality(unittest.TestCase):
    def test_example_fences_are_at_most_five_lines(self):
        for lid in M0:
            for key,source in blocks(lid).items():
                with self.subTest(lesson=lid,source=key):
                    lines=[ln for ln in source.strip().splitlines() if ln.strip()]
                    self.assertLessEqual(len(lines),5,f'{key} 示例超过 5 行')

    def test_no_ahead_knowledge_words_in_prose(self):
        for lid in M0:
            text=md_text(lid)
            with self.subTest(lesson=lid):
                for word in BANNED_WORDS:
                    self.assertIsNone(re.search(r'(?<![A-Za-z])'+word+r'(?![A-Za-z])',text,re.I),f'超纲词 {word}')
                for word in BANNED_ZH:
                    self.assertNotIn(word,text,f'超纲词 {word}')

    def test_quizzes_probe_operations_not_terminology(self):
        all_quizzes=[q for lid in M0 for q in quizzes(lid)]
        self.assertEqual(len(all_quizzes),6)
        for q in all_quizzes:
            text=q['promptMd']+'\n'+'\n'.join(o['textMd'] for o in q['options'])
            with self.subTest(qid=q['questionId']):
                for word in BANNED_WORDS:
                    self.assertIsNone(re.search(r'(?<![A-Za-z])'+word+r'(?![A-Za-z])',text,re.I),f'小测出现超纲词 {word}')
                for word in BANNED_ZH:
                    self.assertNotIn(word,text,f'小测出现超纲词 {word}')
        by_id={q['questionId']:q for q in all_quizzes}
        self.assertIn('哪里',by_id['m0-first-run-q1']['promptMd'])
        self.assertIn('为什么',by_id['m0-first-run-q2']['promptMd'])
        self.assertIn('屏幕上会显示什么',by_id['m0-reading-code-q1']['promptMd'])
        self.assertIn('注释',by_id['m0-reading-code-q2']['promptMd'])
        self.assertIn('错误类型',by_id['m0-when-errors-q1']['promptMd'])
        self.assertIn('先检查哪里',by_id['m0-when-errors-q2']['promptMd'])

    def test_practice_has_seven_sub_steps(self):
        practice=next(s for s in MODEL['lessons']['m0-when-errors']['steps'] if s['type']=='practice')
        self.assertEqual(len(re.findall(r'(?m)^\s*\d+\.\s',practice['taskMd'])),7,'实践子任务数')
        self.assertEqual(len(practice['acceptance']),7,'验收清单条数')

    def test_first_mention_of_key_terms_is_explained(self):
        goal=next(s for s in MODEL['lessons']['m0-first-run']['steps'] if s['id']=='s-goal')['bodyMd']
        self.assertIn('运行',goal);self.assertIn('就是让 Python 把文件里的指令真正执行一遍',goal)
        self.assertIn('输出',goal);self.assertIn('就是执行之后显示出来的文字结果',goal)
        comment=next(s for s in MODEL['lessons']['m0-reading-code']['steps'] if s['id']=='s-comment')['bodyMd']
        self.assertIn('注释',comment);self.assertIn('解释说明的文字',comment)

if __name__=='__main__':unittest.main()
