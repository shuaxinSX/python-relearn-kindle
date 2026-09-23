#!/usr/bin/env python3
"""内容校验器：校验 config.yaml、content/course.yaml 与 content/lessons/*.yaml。

可直接运行::

    python tools/validate.py

也可 import 调用::

    from tools import validate
    errors = validate.validate_all(content_dir, config_path, course_path)

所有错误都会被收集并返回（不静默跳过）；错误信息包含文件路径、
步骤 ID 或题目 ID。返回空列表表示通过。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

ID_RE = re.compile(r"^[a-z0-9-]+$")
SCHEMA_VERSION = 1
STEP_TYPES = ("read", "reveal", "quiz", "practice")
STATUSES = ("draft", "published")


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise yaml.constructor.ConstructorError(None, None,
                f"重复或非字符串 YAML 键: {key!r}", key_node.start_mark)
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------

def is_nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_id(value, what: str, where: str, errors: list) -> bool:
    """检查 ID 合法性（小写字母/数字/短横线），非法则记录错误。"""
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        errors.append(f"{where}: {what} 非法，仅允许小写字母、数字、短横线: {value!r}")
        return False
    return True


def load_yaml(path: Path, errors: list):
    """safe_load 读取 YAML；解析失败返回 None 并记录错误。"""
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.load(f, Loader=UniqueLoader)
    except FileNotFoundError:
        errors.append(f"{path}: 文件不存在")
        return None
    except yaml.YAMLError as exc:
        errors.append(f"{path}: YAML 解析失败: {exc}")
        return None


# --------------------------------------------------------------------------
# config.yaml
# --------------------------------------------------------------------------

def validate_config(config_path: Path, errors: list) -> dict | None:
    cfg = load_yaml(config_path, errors)
    where = str(config_path)
    if cfg is None:
        return None
    if not isinstance(cfg, dict):
        errors.append(f"{where}: 顶层必须是映射")
        return None
    if not is_nonempty_str(cfg.get("siteId")):
        errors.append(f"{where}: siteId 必须为非空字符串")
    base_path = cfg.get("basePath")
    if not isinstance(base_path, str) or not base_path.startswith("/") or not base_path.endswith("/"):
        errors.append(f"{where}: basePath 必须是以 / 开头和结尾的字符串: {base_path!r}")
    return cfg


# --------------------------------------------------------------------------
# course.yaml
# --------------------------------------------------------------------------

def validate_course(course_path: Path, content_dir: Path, errors: list) -> list:
    """校验目录；返回按目录顺序排列的课程 ID 列表。"""
    course = load_yaml(course_path, errors)
    where = str(course_path)
    order: list = []
    if course is None:
        return order
    if not isinstance(course, dict):
        errors.append(f"{where}: 顶层必须是映射")
        return order

    if not is_int(course.get("schemaVersion")) or course.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"{where}: schemaVersion 必须为 {SCHEMA_VERSION}")
    if not is_nonempty_str(course.get("courseId")):
        errors.append(f"{where}: courseId 必须为非空字符串")
    if not is_nonempty_str(course.get("title")):
        errors.append(f"{where}: title 必须为非空字符串")
    if not isinstance(course.get("pythonVersion"), str) or not course.get("pythonVersion"):
        errors.append(f"{where}: pythonVersion 必须为非空字符串")

    modules = course.get("modules")
    if not isinstance(modules, list) or not modules:
        errors.append(f"{where}: modules 必须为非空列表")
        return order

    seen_module_ids: set = set()
    seen_lesson_ids: set = set()
    for mi, module in enumerate(modules):
        mwhere = f"{where}: modules[{mi}]"
        if not isinstance(module, dict):
            errors.append(f"{mwhere}: 模块必须是映射")
            continue
        mid = module.get("id")
        if check_id(mid, "模块 id", mwhere, errors):
            if mid in seen_module_ids:
                errors.append(f"{mwhere}: 模块 id 重复: {mid!r}")
            seen_module_ids.add(mid)
        if not is_nonempty_str(module.get("title")):
            errors.append(f"{mwhere}: 模块 title 必须为非空字符串")
        lesson_ids = module.get("lessonIds")
        if not isinstance(lesson_ids, list) or not all(isinstance(x, str) for x in lesson_ids):
            errors.append(f"{mwhere}: lessonIds 必须为字符串列表")
            continue
        for li, lesson_id in enumerate(lesson_ids):
            lwhere = f"{mwhere}: lessonIds[{li}]"
            if not check_id(lesson_id, "课程 id", lwhere, errors):
                continue
            if lesson_id in seen_lesson_ids:
                errors.append(f"{lwhere}: 课程 id 在目录中重复: {lesson_id!r}")
                continue
            seen_lesson_ids.add(lesson_id)
            lesson_file = content_dir / "lessons" / f"{lesson_id}.yaml"
            if not lesson_file.is_file():
                errors.append(f"{lwhere}: 目录中缺课，课程文件不存在: {lesson_file}")
                continue
            order.append(lesson_id)
    return order


# --------------------------------------------------------------------------
# 单课 YAML
# --------------------------------------------------------------------------

def _validate_quiz(step: dict, swhere: str, errors: list, question_ids: dict):
    step_id = step.get("id")
    qid = step.get("questionId")
    qwhere = f"{swhere}: 题目 {qid!r}"
    if not check_id(qid, "questionId", swhere, errors):
        return
    if qid in question_ids:
        errors.append(f"{qwhere}: questionId 全站重复，首次出现在 {question_ids[qid]}")
    else:
        question_ids[qid] = swhere
    if not is_int(step.get("revision")) or step.get("revision") < 1:
        errors.append(f"{qwhere}: revision 必须为正整数")
    if not is_nonempty_str(step.get("promptMd")):
        errors.append(f"{qwhere}: promptMd 必须为非空字符串")
    if not is_nonempty_str(step.get("explanationMd")):
        errors.append(f"{qwhere}: explanationMd 不得为空")

    options = step.get("options")
    if not isinstance(options, list) or not (2 <= len(options) <= 4):
        errors.append(f"{qwhere}: options 必须为 2—4 个选项的列表")
        return
    seen_opt_ids: set = set()
    for oi, opt in enumerate(options):
        owhere = f"{qwhere}: options[{oi}]"
        if not isinstance(opt, dict):
            errors.append(f"{owhere}: 选项必须是映射")
            continue
        oid = opt.get("id")
        if check_id(oid, "选项 id", owhere, errors):
            if oid in seen_opt_ids:
                errors.append(f"{owhere}: 选项 id 在题内重复: {oid!r}")
            seen_opt_ids.add(oid)
        if not is_nonempty_str(opt.get("textMd")):
            errors.append(f"{owhere}: 选项 {oid!r} 的 textMd 不得为空")
        if not is_nonempty_str(opt.get("explanationMd")):
            errors.append(f"{owhere}: 选项 {oid!r} 的 explanationMd 不得为空（空解释不允许）")
    correct = step.get("correctOptionId")
    if not isinstance(correct, str) or correct not in seen_opt_ids:
        errors.append(f"{qwhere}: correctOptionId {correct!r} 必须存在于 options 中")


def _validate_practice(step: dict, swhere: str, errors: list, practice_count: list):
    practice_count[0] += 1
    step_id = step.get("id")
    pwhere = f"{swhere}: 实践步骤 {step_id!r}"
    if practice_count[0] > 1:
        errors.append(f"{pwhere}: 一课最多只能有一个 practice 步骤")
    for field in ("taskMd", "hintMd", "solutionMd"):
        if not is_nonempty_str(step.get(field)):
            errors.append(f"{pwhere}: {field} 必须为非空字符串")
    acceptance = step.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        errors.append(f"{pwhere}: acceptance 必须为非空列表")
    elif not all(is_nonempty_str(x) for x in acceptance):
        errors.append(f"{pwhere}: acceptance 各项必须为非空字符串")


def validate_lesson(lesson_id: str, lesson_path: Path, order: list, errors: list,
                    question_ids: dict) -> dict | None:
    lesson = load_yaml(lesson_path, errors)
    where = str(lesson_path)
    if lesson is None:
        return None
    if not isinstance(lesson, dict):
        errors.append(f"{where}: 顶层必须是映射")
        return None

    if not is_int(lesson.get("schemaVersion")) or lesson.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"{where}: schemaVersion 必须为 {SCHEMA_VERSION}")
    lid = lesson.get("id")
    if check_id(lid, "课程 id", where, errors):
        if lid != lesson_id:
            errors.append(f"{where}: 课程 id {lid!r} 与文件名 {lesson_id}.yaml 不一致")
    if not is_nonempty_str(lesson.get("title")):
        errors.append(f"{where}: title 必须为非空字符串")
    if not is_nonempty_str(lesson.get("goal")):
        errors.append(f"{where}: goal 必须为非空字符串")
    if not is_int(lesson.get("revision")) or lesson.get("revision") < 1:
        errors.append(f"{where}: revision 必须为正整数")
    status = lesson.get("status")
    if status not in STATUSES:
        errors.append(f"{where}: status 非法 {status!r}，仅允许 draft/published")

    prereqs = lesson.get("prerequisites")
    if not isinstance(prereqs, list) or not all(isinstance(x, str) for x in prereqs):
        errors.append(f"{where}: prerequisites 必须为字符串列表")
    else:
        try:
            pos = order.index(lesson_id)
        except ValueError:
            pos = None
        for pre in prereqs:
            if pre not in order:
                errors.append(f"{where}: 前置课 {pre!r} 在目录顺序中不存在")
            elif pos is not None and order.index(pre) >= pos:
                errors.append(f"{where}: 前置课 {pre!r} 必须在目录顺序中排在前面")

    steps = lesson.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(f"{where}: steps 必须为非空列表")
        return lesson

    seen_step_ids: set = set()
    practice_count = [0]
    for si, step in enumerate(steps):
        swhere = f"{where}: steps[{si}]"
        if not isinstance(step, dict):
            errors.append(f"{swhere}: 步骤必须是映射")
            continue
        sid = step.get("id")
        if check_id(sid, "步骤 id", swhere, errors):
            if sid in seen_step_ids:
                errors.append(f"{swhere}: 步骤 id 在课内重复: {sid!r}")
            seen_step_ids.add(sid)
        swhere = f"{where}: 步骤 {sid!r}"
        stype = step.get("type")
        if stype not in STEP_TYPES:
            errors.append(f"{swhere}: 未知步骤类型 {stype!r}，仅允许 {STEP_TYPES}")
            continue
        if not is_nonempty_str(step.get("title")):
            errors.append(f"{swhere}: 步骤 title 必须为非空字符串")

        if stype == "read":
            if not is_nonempty_str(step.get("bodyMd")):
                errors.append(f"{swhere}: read 步骤的 bodyMd 不得为空")
        elif stype == "reveal":
            for field in ("bodyMd", "revealLabel", "revealMd"):
                if not is_nonempty_str(step.get(field)):
                    errors.append(f"{swhere}: reveal 步骤的 {field} 不得为空")
        elif stype == "quiz":
            _validate_quiz(step, swhere, errors, question_ids)
        elif stype == "practice":
            _validate_practice(step, swhere, errors, practice_count)
    return lesson


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------

def load_model(content_dir: Path, course_path: Path):
    """加载目录与课程数据（供构建器使用；调用前应先通过校验）。"""
    course = load_yaml(course_path, [])
    order: list = []
    lessons: dict = {}
    modules = []
    if isinstance(course, dict):
        for module in course.get("modules") or []:
            if not isinstance(module, dict):
                continue
            lesson_ids = [x for x in (module.get("lessonIds") or []) if isinstance(x, str)]
            modules.append({"id": module.get("id"), "title": module.get("title"),
                            "lessonIds": lesson_ids})
            order.extend(lesson_ids)
    for lesson_id in order:
        lesson = load_yaml(content_dir / "lessons" / f"{lesson_id}.yaml", [])
        if isinstance(lesson, dict):
            lessons[lesson_id] = lesson
    return {"course": course or {}, "order": order, "lessons": lessons, "modules": modules}


def validate_all(content_dir: Path, config_path: Path, course_path: Path) -> list:
    """执行全部校验，返回错误信息列表（空列表表示通过）。"""
    errors: list = []
    validate_config(config_path, errors)
    order = validate_course(course_path, content_dir, errors)
    question_ids: dict = {}
    for lesson_id in order:
        validate_lesson(lesson_id, content_dir / "lessons" / f"{lesson_id}.yaml",
                        order, errors, question_ids)
    for path in sorted((content_dir / "lessons").glob("*.yaml")):
        if path.stem not in order:
            errors.append(f"{path}: 课程文件未在目录中声明")
    if errors:
        return errors
    model = load_model(content_dir, course_path)
    for lid, lesson in model["lessons"].items():
        if lesson.get("status") == "published":
            for pre in lesson.get("prerequisites") or []:
                if isinstance(pre, str) and model["lessons"].get(pre, {}).get("status") == "draft":
                    errors.append(f"{lid}: published 课程依赖 draft 前置课 {pre}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="校验课程内容 YAML")
    parser.add_argument("--config", default=str(REPO_ROOT / "config.yaml"))
    parser.add_argument("--course", default=str(REPO_ROOT / "content" / "course.yaml"))
    parser.add_argument("--content", default=str(REPO_ROOT / "content"))
    args = parser.parse_args(argv)

    errors = validate_all(Path(args.content), Path(args.config), Path(args.course))
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"校验失败：{len(errors)} 个错误", file=sys.stderr)
        return 1
    print("校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
