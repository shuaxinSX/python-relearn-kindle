#!/usr/bin/env python3
"""样课 YAML 蓝图符合性测试（对照 v1-content-spec.md §4.01 与 §9）。

读真实 content/lessons/run-and-bindings.yaml，断言步骤结构、
两道小测的题号/正确项/选项数/解析非空/误解关键词、reveal 标签。
"""

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LESSON_PATH = REPO_ROOT / "content" / "lessons" / "run-and-bindings.yaml"


def load_lesson():
    return yaml.safe_load(LESSON_PATH.read_text(encoding="utf-8"))


class TestSampleLessonBlueprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lesson = load_lesson()
        cls.steps = cls.lesson["steps"]
        cls.by_id = {s["id"]: s for s in cls.steps}
        cls.quizzes = [s for s in cls.steps if s["type"] == "quiz"]

    # -- 步骤结构 ---------------------------------------------------------
    def test_seven_steps_in_order(self):
        """样课 7 步，步骤 ID 顺序符合蓝图。"""
        ids = [s["id"] for s in self.steps]
        self.assertEqual(ids, [
            "s-goal", "s-mechanism", "s-predict", "s-misconception",
            "s-quiz-1", "s-quiz-2", "s-recap",
        ])

    def test_step_types_only_allowed(self):
        """步骤类型仅 read/reveal/quiz。"""
        for s in self.steps:
            self.assertIn(s["type"], ("read", "reveal", "quiz"),
                          f"步骤 {s['id']} 类型 {s['type']} 不在蓝图内")

    def test_seven_step_roles(self):
        """7 步的角色：目标/机制/预测展开/误区/小测1/小测2/总结。"""
        types = [s["type"] for s in self.steps]
        self.assertEqual(types,
                         ["read", "read", "reveal", "reveal", "quiz", "quiz", "read"])

    # -- 两道小测 -----------------------------------------------------------
    def test_question_ids_and_correct_options(self):
        """questionId 与 correctOptionId 与蓝图锁定的一致。"""
        q1, q2 = self.quizzes
        self.assertEqual(q1["questionId"], "run-and-bindings-q1")
        self.assertEqual(q2["questionId"], "run-and-bindings-q2")
        self.assertEqual(q1["correctOptionId"], "b")
        self.assertEqual(q2["correctOptionId"], "a")

    def test_correct_option_text_q1(self):
        """q1 正确选项 textMd 含 '2 3'。"""
        q1 = self.quizzes[0]
        correct = next(o for o in q1["options"]
                       if o["id"] == q1["correctOptionId"])
        self.assertIn("2 3", correct["textMd"])

    def test_correct_option_text_q2(self):
        """q2 正确选项 textMd 含 60。"""
        q2 = self.quizzes[1]
        correct = next(o for o in q2["options"]
                       if o["id"] == q2["correctOptionId"])
        self.assertIn("60", correct["textMd"])

    def test_option_counts(self):
        """每题 3—4 个选项。"""
        for q in self.quizzes:
            self.assertGreaterEqual(len(q["options"]), 3,
                                    f"题目 {q['questionId']} 选项不足 3 个")
            self.assertLessEqual(len(q["options"]), 4,
                                 f"题目 {q['questionId']} 选项超过 4 个")

    def test_explanations_nonempty(self):
        """每题总解析与每个选项 explanationMd 均非空。"""
        for q in self.quizzes:
            qid = q["questionId"]
            self.assertTrue(q["explanationMd"].strip(),
                            f"题目 {qid} 的 explanationMd 为空")
            for opt in q["options"]:
                self.assertTrue(opt["explanationMd"].strip(),
                                f"题目 {qid} 选项 {opt['id']} 的 explanationMd 为空")
                self.assertTrue(opt["textMd"].strip(),
                                f"题目 {qid} 选项 {opt['id']} 的 textMd 为空")

    def test_wrong_options_mention_misconceptions(self):
        """每个错选项的解析提到对应的误解关键词。"""
        keywords = {
            "run-and-bindings-q1": ("联动", "只执行一次", "同时更新"),
            "run-and-bindings-q2": ("重算", "自动", "更新"),
        }
        for q in self.quizzes:
            qid = q["questionId"]
            for opt in q["options"]:
                if opt["id"] == q["correctOptionId"]:
                    continue
                text = opt["explanationMd"]
                self.assertTrue(
                    any(k in text for k in keywords[qid]),
                    f"题目 {qid} 错选项 {opt['id']} 的解析未提及误解关键词 "
                    f"{keywords[qid]}（实际文本: {text[:60]}…）")

    def test_q1_distractors_cover_blueprint(self):
        """q1 三个干扰项分别覆盖蓝图的三种误解诊断。"""
        q1 = self.quizzes[0]
        wrong = {o["id"]: o["explanationMd"] for o in q1["options"]
                 if o["id"] != q1["correctOptionId"]}
        self.assertIn("只执行一次", wrong["a"])
        self.assertIn("联动", wrong["c"])
        self.assertIn("同时更新", wrong["d"])

    # -- reveal 步骤 ---------------------------------------------------------
    def test_reveal_steps_have_label(self):
        """reveal 步骤有 revealLabel。"""
        reveals = [s for s in self.steps if s["type"] == "reveal"]
        self.assertEqual(len(reveals), 2)
        for s in reveals:
            self.assertTrue(s["revealLabel"].strip(),
                            f"步骤 {s['id']} 缺 revealLabel")
            self.assertTrue(s["revealMd"].strip(),
                            f"步骤 {s['id']} 缺 revealMd")


if __name__ == "__main__":
    unittest.main()
