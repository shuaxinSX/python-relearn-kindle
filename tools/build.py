#!/usr/bin/env python3
"""静态站构建器。

流程：读 config.yaml → 内容校验（失败即停）→ Markdown 渲染（禁用原始 HTML）
→ 对 assets 算 sha256 取前 8 位得哈希文件名 → Jinja2（启用自动转义）渲染
页面 → 写 dist/ → 内链检查 → 体积检查并打印报告。

用法::

    python tools/build.py [--base-path /] [--out dist]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, unquote

try:
    from tools import validate as validator
except ImportError:  # 以 `python tools/build.py` 方式运行时
    import validate as validator

from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

REPO_ROOT = Path(__file__).resolve().parent.parent

HTML_BUDGET = 60 * 1024   # 每页 HTML 上限
JS_BUDGET = 30 * 1024     # 哈希后 JS 上限
CSS_BUDGET = 10 * 1024    # 哈希后 CSS 上限

ASSET_FILES = ("reader.js", "styles.css")

HREF_RE = re.compile(r'href="([^"]*)"')
ID_RE = re.compile(r'(?<![-\w])id="([^"]+)"')


def normalize_base_path(base_path: str) -> str:
    if not base_path.startswith("/"):
        base_path = "/" + base_path
    if not base_path.endswith("/"):
        base_path = base_path + "/"
    return base_path


def render_markdown(md: MarkdownIt, text: str) -> str:
    tokens = md.parse(text)
    def resolve(tokens):
        for token in tokens:
            attr = 'href' if token.type == 'link_open' else ('src' if token.type == 'image' else None)
            ref = token.attrGet(attr) if attr else None
            if ref and not ref.startswith('#') and not urlsplit(ref).scheme and not ref.startswith('//'):
                token.attrSet(attr, urljoin(md.options.get('basePath', '/') + 'lessons/', ref))
            if token.children:
                resolve(token.children)
    resolve(tokens)
    return md.renderer.render(tokens, md.options, {})


def compact_js(source: str) -> str:
    """只移除行首缩进与空行；测试用 ES5 AST 等价检查保护字符串语义。"""
    return "\n".join(line.lstrip() for line in source.splitlines() if line.strip()) + "\n"


def build_lesson_context(lesson: dict, md: MarkdownIt) -> dict:
    steps = []
    for step in lesson.get("steps") or []:
        stype = step.get("type")
        ctx = {"id": step.get("id"), "type": stype, "title": step.get("title")}
        if stype in ("read", "reveal"):
            ctx["body_html"] = render_markdown(md, step.get("bodyMd") or "")
        if stype == "reveal":
            ctx["reveal_label"] = step.get("revealLabel")
            ctx["reveal_html"] = render_markdown(md, step.get("revealMd") or "")
        elif stype == "quiz":
            ctx["question_id"] = step.get("questionId")
            ctx["question_revision"] = step.get("revision")
            ctx["prompt_html"] = render_markdown(md, step.get("promptMd") or "")
            ctx["explanation_html"] = render_markdown(md, step.get("explanationMd") or "")
            ctx["options"] = [
                {"id": opt.get("id"),
                 "text_html": render_markdown(md, opt.get("textMd") or ""),
                 "explanation_html": render_markdown(md, opt.get("explanationMd") or "")}
                for opt in (step.get("options") or [])
            ]
            correct = step.get("correctOptionId")
            ctx["correct_option_id"] = correct
            ctx["correct_opt_html"] = next(
                (o["text_html"] for o in ctx["options"] if o["id"] == correct), "")
        elif stype == "practice":
            ctx["task_html"] = render_markdown(md, step.get("taskMd") or "")
            ctx["hint_html"] = render_markdown(md, step.get("hintMd") or "")
            ctx["solution_html"] = render_markdown(md, step.get("solutionMd") or "")
            ctx["acceptance_html"] = [render_markdown(md, a) for a in (step.get("acceptance") or [])]
        steps.append(ctx)
    return {"id": lesson.get("id"), "title": lesson.get("title"), "goal": lesson.get("goal"),
            "steps": steps,
            "practice_id": next((s["id"] for s in steps if s["type"] == "practice"), None),
            "has_practice": any(s["type"] == "practice" for s in steps)}


def collect_questions(model_lessons: dict, order: list) -> list:
    questions = []
    for lesson_id in order:
        lesson = model_lessons.get(lesson_id)
        if not lesson or lesson.get("status") != "published":
            continue
        for step in lesson.get("steps") or []:
            if step.get("type") == "quiz":
                questions.append({
                    "question_id": step.get("questionId"),
                    "revision": step.get("revision"),
                    "lesson_id": lesson_id,
                    "step_id": step.get("id"),
                    "lesson_title": lesson.get("title"),
                    "step_title": step.get("title"),
                })
    return questions


# --------------------------------------------------------------------------
# 内链检查
# --------------------------------------------------------------------------

def check_links(dist_dir: Path, base_path: str) -> list:
    """所有以 basePath 开头的 href：去掉查询串/锚点后必须对应已生成文件；
    含 # 锚点的必须在目标文件中找到对应 id。"""
    errors: list = []
    html_files = sorted(dist_dir.rglob("*.html"))
    ids_cache: dict = {}

    def ids_of(path: Path) -> set:
        if path not in ids_cache:
            ids_cache[path] = set(ID_RE.findall(path.read_text(encoding="utf-8")))
        return ids_cache[path]

    class References(HTMLParser):
        def __init__(self):
            super().__init__()
            self.refs = []
        def handle_starttag(self, tag, attrs):
            self.refs.extend(v for k, v in attrs if k in ("href", "src") and v)

    for page in html_files:
        rel_page = page.relative_to(dist_dir).as_posix()
        html = page.read_text(encoding="utf-8")
        page_ids = ids_of(page)
        parser = References()
        parser.feed(html)
        for href in parser.refs:
            if urlsplit(href).scheme or href.startswith("//"):
                continue
            if href.startswith("#"):
                frag = href[1:]
                if frag and frag not in page_ids:
                    errors.append(f"{rel_page}: 锚点 #{frag} 在本页不存在")
                continue
            parts = urlsplit(urljoin(base_path + rel_page, href))
            if not parts.path.startswith(base_path):
                errors.append(f"{rel_page}: 内部引用越出 basePath: {href}")
                continue
            rel = unquote(parts.path[len(base_path):])
            if not rel or rel.endswith("/"):
                rel += "index.html"
            target = dist_dir / rel
            if not target.resolve().is_relative_to(dist_dir.resolve()):
                errors.append(f"{rel_page}: 内部引用越出输出目录: {href}")
                continue
            if not target.is_file():
                errors.append(f"{rel_page}: 内链目标不存在: {href}")
                continue
            if parts.fragment and unquote(parts.fragment) not in ids_of(target):
                errors.append(f"{rel_page}: 锚点 #{parts.fragment} 在 {rel} 中不存在 (href={href})")
    return errors


# --------------------------------------------------------------------------
# 体积检查
# --------------------------------------------------------------------------

def check_sizes(dist_dir: Path) -> tuple[list, list]:
    """返回 (报告行, 错误行)。"""
    report: list = []
    errors: list = []

    def kib(n: int) -> str:
        return f"{n / 1024:.1f} KiB"

    for page in sorted(dist_dir.rglob("*.html")):
        rel = page.relative_to(dist_dir).as_posix()
        size = page.stat().st_size
        ok = size <= HTML_BUDGET
        report.append(f"{'PASS' if ok else 'FAIL'}  HTML {rel}: {kib(size)}（预算 {kib(HTML_BUDGET)}）")
        if not ok:
            errors.append(f"{rel}: HTML 体积 {kib(size)} 超过预算 {kib(HTML_BUDGET)}")

    for js in sorted((dist_dir / "assets").glob("reader.*.js")):
        rel = js.relative_to(dist_dir).as_posix()
        size = js.stat().st_size
        ok = size <= JS_BUDGET
        report.append(f"{'PASS' if ok else 'FAIL'}  JS   {rel}: {kib(size)}（预算 {kib(JS_BUDGET)}）")
        if not ok:
            errors.append(f"{rel}: JS 体积 {kib(size)} 超过预算 {kib(JS_BUDGET)}")

    for css in sorted((dist_dir / "assets").glob("styles.*.css")):
        rel = css.relative_to(dist_dir).as_posix()
        size = css.stat().st_size
        ok = size <= CSS_BUDGET
        report.append(f"{'PASS' if ok else 'FAIL'}  CSS  {rel}: {kib(size)}（预算 {kib(CSS_BUDGET)}）")
        if not ok:
            errors.append(f"{rel}: CSS 体积 {kib(size)} 超过预算 {kib(CSS_BUDGET)}")
    return report, errors


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="构建 Python 重学微课静态站")
    parser.add_argument("--base-path", default=None,
                        help="覆盖 config.yaml 中的 basePath（CI 按仓库名计算）")
    parser.add_argument("--out", default="dist", help="输出目录（默认 dist）")
    parser.add_argument("--config", default=str(REPO_ROOT / "config.yaml"))
    parser.add_argument("--course", default=str(REPO_ROOT / "content" / "course.yaml"))
    parser.add_argument("--content", default=str(REPO_ROOT / "content"))
    args = parser.parse_args(argv)

    content_dir = Path(args.content)
    config_path = Path(args.config)
    course_path = Path(args.course)
    out_dir = Path(args.out)
    protected = [REPO_ROOT / name for name in ('content', 'assets', 'templates', 'tools', 'tests', 'docs', '.git', '.github', '.venv', 'node_modules')]
    resolved_out = out_dir.resolve()
    if (REPO_ROOT.is_relative_to(resolved_out) or
            any(resolved_out.is_relative_to(p) for p in protected)):
        print(f"构建中止：输出目录不可覆盖项目源码: {out_dir}", file=sys.stderr)
        return 1

    # 1. 读配置
    config_errors: list = []
    cfg = validator.validate_config(config_path, config_errors)
    if config_errors or cfg is None:
        for err in config_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print("构建中止：config.yaml 校验失败", file=sys.stderr)
        return 1
    base_path = normalize_base_path(args.base_path or cfg.get("basePath", "/"))
    site_id = cfg.get("siteId")
    course_title = cfg.get("title") or "Python 重学微课"
    print(f"basePath={base_path} siteId={site_id}")

    # 2. 内容校验（失败即停）
    errors = validator.validate_all(content_dir, config_path, course_path)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"构建中止：内容校验失败（{len(errors)} 个错误）", file=sys.stderr)
        return 1
    print("内容校验通过")

    model = validator.load_model(content_dir, course_path)
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    md.options['basePath'] = base_path

    # 3. 资源哈希（先算哈希，再渲染模板）
    assets_src = REPO_ROOT / "assets"
    hashed: dict = {}
    asset_bytes: dict = {}
    for name in ASSET_FILES:
        src = assets_src / name
        if not src.is_file():
            print(f"构建中止：资源文件缺失: {src}", file=sys.stderr)
            return 1
        asset_bytes[name] = (compact_js(src.read_text(encoding="utf-8")).encode("utf-8")
                             if name.endswith(".js") else src.read_bytes())
        digest = hashlib.sha256(asset_bytes[name]).hexdigest()[:8]
        stem, suffix = name.rsplit(".", 1)
        hashed[name] = f"{stem}.{digest}.{suffix}"

    def url(page: str) -> str:
        return base_path + page

    def asset(name: str) -> str:
        return base_path + "assets/" + hashed[name]

    # window.PRL_CONFIG 由构建器生成 JSON（注意转义）
    prl_config = json.dumps({"siteId": site_id, "basePath": base_path,
                            "courseId": model["course"]["courseId"]},
                            ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    prl_config_js = f"window.PRL_CONFIG={prl_config};"

    env = Environment(loader=FileSystemLoader(REPO_ROOT / "templates"), autoescape=True)
    env.globals["url"] = url
    env.globals["asset"] = asset

    # 4. 组装模板上下文（只发布 published 课程）
    lessons_ctx = {}
    published_order = []
    for lesson_id in model["order"]:
        lesson = model["lessons"].get(lesson_id)
        if lesson and lesson.get("status") == "published":
            lessons_ctx[lesson_id] = build_lesson_context(lesson, md)
            published_order.append(lesson_id)

    seq = 0
    modules_ctx = []
    for module in model["modules"]:
        items = []
        for lesson_id in module["lessonIds"]:
            if lesson_id in lessons_ctx:
                seq += 1
                items.append({**lessons_ctx[lesson_id], "seq": seq})
        if items:
            modules_ctx.append({"id": module["id"], "title": module["title"], "lessons": items})

    all_lessons = [lessons_ctx[lid] for lid in published_order]
    for i, lesson in enumerate(all_lessons):
        lesson["seq"] = i + 1
    questions = collect_questions(model["lessons"], model["order"])

    base_ctx = {"course_title": course_title, "prl_config_js": prl_config_js}

    pages: dict[str, str] = {}
    pages["index.html"] = env.get_template("index.html").render(
        **base_ctx, page_kind="index", lessons=all_lessons, questions=questions, total=len(all_lessons))
    pages["course.html"] = env.get_template("course.html").render(
        **base_ctx, page_kind="course", modules=modules_ctx)
    pages["review.html"] = env.get_template("review.html").render(
        **base_ctx, page_kind="review", questions=questions)
    pages["settings.html"] = env.get_template("settings.html").render(
        **base_ctx, page_kind="settings", lessons=all_lessons, questions=questions)
    pages["404.html"] = env.get_template("404.html").render(**base_ctx, page_kind="404")

    lesson_tpl = env.get_template("lesson.html")
    for i, lesson_id in enumerate(published_order):
        lesson = lessons_ctx[lesson_id]
        nxt = lessons_ctx[published_order[i + 1]] if i + 1 < len(published_order) else None
        pages[f"lessons/{lesson_id}.html"] = lesson_tpl.render(
            **base_ctx, page_kind="lesson", lesson=lesson, next_lesson=nxt)

    # 5. 写 dist/
    if out_dir.exists():
        for child in sorted(out_dir.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    (out_dir / "lessons").mkdir(parents=True, exist_ok=True)
    for rel, html in pages.items():
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    for name, hashed_name in hashed.items():
        (out_dir / "assets" / hashed_name).write_bytes(asset_bytes[name])
    samples = content_dir / "samples"
    if samples.is_dir():
        for sample in samples.iterdir():
            if sample.is_file():
                target = out_dir / "exercises" / sample.name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(sample.read_bytes())
    print(f"已生成 {len(pages)} 个页面 + {len(hashed)} 个资源 → {out_dir}")

    # 6. 内链检查
    link_errors = check_links(out_dir, base_path)
    if link_errors:
        for err in link_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"构建失败：内链检查发现 {len(link_errors)} 个问题", file=sys.stderr)
        return 1
    print("内链检查通过")

    # 7. 体积检查并打印报告
    size_report, size_errors = check_sizes(out_dir)
    print("体积报告（未压缩）：")
    for line in size_report:
        print("  " + line)
    if size_errors:
        for err in size_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print("构建失败：体积预算超限", file=sys.stderr)
        return 1

    print("构建成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
