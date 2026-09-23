#!/usr/bin/env python3
"""validator 负例测试。

在临时目录里构造最小内容集（不污染 content/），逐项触发
tools/validate.py 的报错。每个负例断言两点：
  1. validate.main(argv) 返回码 != 0（非零退出）；
  2. stderr 错误信息中包含文件路径 / 步骤 ID / 题目 ID（能定位问题）。
"""

import contextlib
import copy
import io
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate  # noqa: E402


# --------------------------------------------------------------------------
# 最小合法内容集（测试用，不触碰真实 content/）
# --------------------------------------------------------------------------

def make_quiz(question_id, correct="b", **overrides):
    quiz = {
        "id": "s-quiz-x",
        "type": "quiz",
        "title": "小测",
        "questionId": question_id,
        "revision": 1,
        "promptMd": "题干",
        "options": [
            {"id": "a", "textMd": "选项 A", "explanationMd": "错因 A"},
            {"id": "b", "textMd": "选项 B", "explanationMd": "正确"},
        ],
        "correctOptionId": correct,
        "explanationMd": "总解析",
    }
    quiz.update(overrides)
    return quiz


def make_lesson(lesson_id, **overrides):
    lesson = {
        "schemaVersion": 1,
        "id": lesson_id,
        "title": f"课 {lesson_id}",
        "goal": "目标",
        "revision": 1,
        "status": "published",
        "prerequisites": [],
        "steps": [
            {"id": "s-read", "type": "read", "title": "阅读", "bodyMd": "正文"},
            {
                "id": "s-reveal", "type": "reveal", "title": "展开",
                "bodyMd": "问题", "revealLabel": "展开", "revealMd": "结果",
            },
            make_quiz(f"{lesson_id}-q1", correct="b"),
        ],
    }
    lesson.update(overrides)
    return lesson


def make_practice_step(step_id="s-practice"):
    return {
        "id": step_id, "type": "practice", "title": "实践",
        "taskMd": "任务", "hintMd": "提示", "solutionMd": "参考解法",
        "acceptance": ["验收 1"],
    }


def write_set(tmpdir, lessons, config=None, course=None):
    """把内容集写进临时目录，返回 (content_dir, config_path, course_path)。"""
    tmp = Path(tmpdir)
    if config is None:
        config = {"siteId": "test-site", "basePath": "/"}
    if course is None:
        course = {
            "schemaVersion": 1,
            "courseId": "test-course",
            "title": "测试课程",
            "pythonVersion": "3.13",
            "modules": [
                {"id": "m1", "title": "M1", "lessonIds": list(lessons.keys())}
            ],
        }
    config_path = tmp / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    content_dir = tmp / "content"
    (content_dir / "lessons").mkdir(parents=True, exist_ok=True)
    course_path = content_dir / "course.yaml"
    course_path.write_text(yaml.safe_dump(course, allow_unicode=True), encoding="utf-8")
    for lesson_id, lesson in lessons.items():
        (content_dir / "lessons" / f"{lesson_id}.yaml").write_text(
            yaml.safe_dump(lesson, allow_unicode=True), encoding="utf-8")
    return content_dir, config_path, course_path


class ValidateNegativeBase(unittest.TestCase):
    """负例通用断言：返回码非零 + 错误信息含定位标识。"""

    def run_negative(self, lessons, needle, config=None, course=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            content_dir, config_path, course_path = write_set(
                tmpdir, lessons, config=config, course=course)
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = validate.main([
                    "--config", str(config_path),
                    "--course", str(course_path),
                    "--content", str(content_dir),
                ])
            stderr = buf.getvalue()
        self.assertNotEqual(rc, 0, f"期望非零退出，实际 {rc}；stderr={stderr!r}")
        self.assertIn(needle, stderr,
                      f"错误信息应包含定位标识 {needle!r}；stderr={stderr!r}")
        return stderr


class TestLessonFields(ValidateNegativeBase):
    def test_missing_required_field(self):
        """缺必填字段：title 缺失。"""
        lesson = make_lesson("lesson-a")
        del lesson["title"]
        stderr = self.run_negative({"lesson-a": lesson}, "lesson-a.yaml")
        self.assertIn("title", stderr)

    def test_wrong_field_type(self):
        """字段类型错：revision 应为整数，给成字符串。"""
        lesson = make_lesson("lesson-a", revision="one")
        stderr = self.run_negative({"lesson-a": lesson}, "lesson-a.yaml")
        self.assertIn("revision", stderr)

    def test_unknown_step_type(self):
        """未知步骤类型。"""
        lesson = make_lesson("lesson-a")
        lesson["steps"][0]["type"] = "video"
        stderr = self.run_negative({"lesson-a": lesson}, "s-read")
        self.assertIn("未知步骤类型", stderr)

    def test_duplicate_step_id(self):
        """步骤 ID 课内重复。"""
        lesson = make_lesson("lesson-a")
        dup = copy.deepcopy(lesson["steps"][0])
        lesson["steps"].append(dup)
        stderr = self.run_negative({"lesson-a": lesson}, "s-read")
        self.assertIn("重复", stderr)

    def test_invalid_status(self):
        """非法 status。"""
        lesson = make_lesson("lesson-a", status="archived")
        stderr = self.run_negative({"lesson-a": lesson}, "lesson-a.yaml")
        self.assertIn("status", stderr)

    def test_two_practice_steps(self):
        """一课两个 practice 步骤。"""
        lesson = make_lesson("lesson-a")
        lesson["steps"].append(make_practice_step("s-practice-1"))
        lesson["steps"].append(make_practice_step("s-practice-2"))
        stderr = self.run_negative({"lesson-a": lesson}, "practice")
        self.assertIn("最多", stderr)

    def test_reveal_missing_reveal_label(self):
        """reveal 步骤缺 revealLabel。"""
        lesson = make_lesson("lesson-a")
        del lesson["steps"][1]["revealLabel"]
        stderr = self.run_negative({"lesson-a": lesson}, "s-reveal")
        self.assertIn("revealLabel", stderr)

    def test_prerequisite_not_exist(self):
        """前置课在目录顺序中不存在。"""
        lesson = make_lesson("lesson-a", prerequisites=["ghost-lesson"])
        stderr = self.run_negative({"lesson-a": lesson}, "ghost-lesson")
        self.assertIn("前置课", stderr)

    def test_prerequisite_not_before(self):
        """前置课存在但不在当前课前面（顺序错误）。"""
        lesson_a = make_lesson("lesson-a")
        lesson_b = make_lesson("lesson-b")
        lesson_a["prerequisites"] = ["lesson-b"]  # 目录顺序 a 在前，b 在后
        stderr = self.run_negative({"lesson-a": lesson_a, "lesson-b": lesson_b},
                                   "lesson-b")
        self.assertIn("排在前面", stderr)


class TestQuizRules(ValidateNegativeBase):
    def _quiz_lessons(self, mutate):
        lesson = make_lesson("lesson-a")
        mutate(lesson["steps"][2])
        return {"lesson-a": lesson}

    def test_duplicate_question_id(self):
        """题目 ID 全站重复。"""
        lessons = {
            "lesson-a": make_lesson("lesson-a"),
            "lesson-b": make_lesson("lesson-b"),
        }
        lessons["lesson-b"]["steps"][2]["questionId"] = "lesson-a-q1"
        stderr = self.run_negative(lessons, "lesson-a-q1")
        self.assertIn("全站重复", stderr)

    def test_duplicate_option_id(self):
        """选项 ID 题内重复。"""
        lessons = self._quiz_lessons(lambda q: q["options"].append(
            {"id": "a", "textMd": "又一个 A", "explanationMd": "错因"}))
        stderr = self.run_negative(lessons, "lesson-a-q1")
        self.assertIn("题内重复", stderr)

    def test_correct_option_missing(self):
        """correctOptionId 不存在于 options。"""
        lessons = self._quiz_lessons(lambda q: q.update(correctOptionId="z"))
        stderr = self.run_negative(lessons, "lesson-a-q1")
        self.assertIn("correctOptionId", stderr)

    def test_empty_question_explanation(self):
        """题目 explanationMd 为空。"""
        lessons = self._quiz_lessons(lambda q: q.update(explanationMd="  "))
        stderr = self.run_negative(lessons, "lesson-a-q1")
        self.assertIn("explanationMd", stderr)

    def test_empty_option_explanation(self):
        """选项级 explanationMd 为空。"""
        def mutate(q):
            q["options"][0]["explanationMd"] = ""
        stderr = self.run_negative(self._quiz_lessons(mutate), "lesson-a-q1")
        self.assertIn("explanationMd", stderr)

    def test_too_few_options(self):
        """选项不足 2 个。"""
        def mutate(q):
            q["options"] = q["options"][:1]
        stderr = self.run_negative(self._quiz_lessons(mutate), "lesson-a-q1")
        self.assertIn("2—4", stderr)

    def test_too_many_options(self):
        """选项超过 4 个。"""
        def mutate(q):
            q["options"] = [
                {"id": f"o{i}", "textMd": f"选项{i}", "explanationMd": "解析"}
                for i in range(5)
            ]
        stderr = self.run_negative(self._quiz_lessons(mutate), "lesson-a-q1")
        self.assertIn("2—4", stderr)


class TestCatalogAndConfig(ValidateNegativeBase):
    def test_duplicate_lesson_id_in_catalog(self):
        """课程 ID 在目录中重复。"""
        lessons = {"lesson-a": make_lesson("lesson-a")}
        course = {
            "schemaVersion": 1, "courseId": "test-course", "title": "测试课程",
            "pythonVersion": "3.13",
            "modules": [
                {"id": "m1", "title": "M1", "lessonIds": ["lesson-a"]},
                {"id": "m2", "title": "M2", "lessonIds": ["lesson-a"]},
            ],
        }
        stderr = self.run_negative(lessons, "lesson-a", course=course)
        self.assertIn("重复", stderr)

    def test_catalog_lesson_file_missing(self):
        """目录 lessonIds 缺课程文件。"""
        lessons = {"lesson-a": make_lesson("lesson-a")}
        course = {
            "schemaVersion": 1, "courseId": "test-course", "title": "测试课程",
            "pythonVersion": "3.13",
            "modules": [{"id": "m1", "title": "M1",
                         "lessonIds": ["lesson-a", "lesson-missing"]}],
        }
        stderr = self.run_negative(lessons, "lesson-missing", course=course)
        self.assertIn("不存在", stderr)

    def test_config_site_id_empty(self):
        """config 非法：siteId 为空。"""
        lessons = {"lesson-a": make_lesson("lesson-a")}
        config = {"siteId": "   ", "basePath": "/"}
        stderr = self.run_negative(lessons, "siteId", config=config)
        self.assertIn("非空", stderr)

    def test_config_base_path_bad(self):
        """config 非法：basePath 不合规（缺开头斜杠 / 缺结尾斜杠）。"""
        lessons = {"lesson-a": make_lesson("lesson-a")}
        for bad in ("repo", "repo/", "http:/x"):
            config = {"siteId": "test-site", "basePath": bad}
            stderr = self.run_negative(lessons, "basePath", config=config)
            self.assertIn("basePath", stderr)


class TestValidSetPasses(unittest.TestCase):
    def test_valid_set_exits_zero(self):
        """最小合法内容集应通过校验（退出码 0）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_dir, config_path, course_path = write_set(
                tmpdir, {"lesson-a": make_lesson("lesson-a"),
                         "lesson-b": make_lesson("lesson-b")})
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = validate.main([
                    "--config", str(config_path),
                    "--course", str(course_path),
                    "--content", str(content_dir),
                ])
        self.assertEqual(rc, 0, f"合法内容集应通过；stderr={buf.getvalue()!r}")


if __name__ == "__main__":
    unittest.main()
