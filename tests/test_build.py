#!/usr/bin/env python3
"""构建器测试：用真实内容构建，检查产物结构、内链、锚点、
静态可读性、quiz 数据一致性、体积预算与 basePath 前缀。
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import build as builder  # noqa: E402

CONFIG = REPO_ROOT / "config.yaml"
COURSE = REPO_ROOT / "content" / "course.yaml"
CONTENT = REPO_ROOT / "content"

HTML_BUDGET = 60 * 1024
JS_BUDGET = 30 * 1024
CSS_BUDGET = 10 * 1024

HREF_RE = re.compile(r'href="([^"]*)"')
SRC_RE = re.compile(r'src="([^"]*)"')
ID_RE = re.compile(r'(?<![-\w])id="([^"]+)"')
DATA_CORRECT_RE = re.compile(
    r'data-question-id="([^"]+)"[^>]*data-correct-option="([^"]+)"')


def build_to(tmpdir, base_path=None):
    """在临时目录构建真实内容，返回 (rc, dist_dir)。"""
    dist = Path(tmpdir) / "dist"
    argv = ["--out", str(dist),
            "--config", str(CONFIG), "--course", str(COURSE),
            "--content", str(CONTENT)]
    if base_path is not None:
        argv += ["--base-path", base_path]
    rc = builder.main(argv)
    return rc, dist


def read_html(dist, rel):
    return (dist / rel).read_text(encoding="utf-8")


class BuildBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        rc, cls.dist = build_to(cls._tmp.name)
        assert rc == 0, "真实内容构建失败，无法继续本组测试"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def pages(self):
        return {p.relative_to(self.dist).as_posix(): p.read_text(encoding="utf-8")
                for p in self.dist.rglob("*.html")}


class TestBuildOutputs(BuildBase):
    def test_build_succeeds(self):
        """构建返回码为 0。"""
        rc, _ = build_to(self._tmp.name)
        self.assertEqual(rc, 0)

    def test_all_twenty_one_pages_exist(self):
        from tests.test_v1 import ORDER
        expected = {"index.html", "course.html", "review.html", "settings.html", "404.html"}
        expected.update("lessons/" + lid + ".html" for lid in ORDER)
        self.assertEqual(set(self.pages()), expected)

    def test_two_hashed_assets_exist(self):
        """2 个哈希资源存在（reader.js / styles.css 各一）。"""
        js = sorted((self.dist / "assets").glob("reader.*.js"))
        css = sorted((self.dist / "assets").glob("styles.*.css"))
        self.assertEqual(len(js), 1, f"reader.js 哈希资源应为 1 个: {js}")
        self.assertEqual(len(css), 1, f"styles.css 哈希资源应为 1 个: {css}")
        self.assertRegex(js[0].name, r"^reader\.[0-9a-f]{8}\.js$")
        self.assertRegex(css[0].name, r"^styles\.[0-9a-f]{8}\.css$")


class TestInternalLinks(BuildBase):
    def _all_refs(self):
        refs = []
        for rel, html in self.pages().items():
            for href in HREF_RE.findall(html):
                refs.append((rel, "href", href))
            for src in SRC_RE.findall(html):
                refs.append((rel, "src", src))
        return refs

    def test_internal_refs_use_base_path(self):
        """所有产物内链以 basePath 开头，无硬编码根路径。"""
        for rel, kind, ref in self._all_refs():
            if not ref or ref.startswith("#") or re.match(r"https?://", ref):
                continue  # 锚点 / 外部链接不在检查范围
            self.assertTrue(
                ref.startswith("/"),
                f"{rel}: {kind}={ref!r} 应以 basePath('/') 开头")

    def test_anchor_ids_exist(self):
        """每个 # 锚点在本页都有对应 id。"""
        for rel, html in self.pages().items():
            ids = set(ID_RE.findall(html))
            for href in HREF_RE.findall(html):
                if href.startswith("#") and len(href) > 1:
                    self.assertIn(href[1:], ids,
                                  f"{rel}: 锚点 {href} 缺对应 id")

    def test_asset_files_resolvable(self):
        """assets 引用能对应到真实文件。"""
        for rel, html in self.pages().items():
            for src in SRC_RE.findall(html):
                if src.startswith("/assets/"):
                    target = self.dist / src.lstrip("/")
                    self.assertTrue(target.is_file(),
                                    f"{rel}: 资源 {src} 不存在")
            for href in HREF_RE.findall(html):
                if href.startswith("/assets/"):
                    target = self.dist / href.lstrip("/")
                    self.assertTrue(target.is_file(),
                                    f"{rel}: 资源 {href} 不存在")


class TestStaticReadability(BuildBase):
    def test_all_lesson_text_anchors_and_answers_are_static(self):
        from tests.content_support import MODEL, fields
        from markdown_it import MarkdownIt
        md = MarkdownIt('commonmark', {'html': False}).enable('table')
        for lid in MODEL['order']:
            html = self.pages()['lessons/' + lid + '.html']
            for field, text in fields(MODEL['lessons'][lid]):
                with self.subTest(lesson=lid, field=field):
                    self.assertIn(builder.render_markdown(md, text), html)
            expected = {s['questionId']: s['correctOptionId']
                        for s in MODEL['lessons'][lid]['steps'] if s['type'] == 'quiz'}
            self.assertEqual(dict(DATA_CORRECT_RE.findall(html)), expected)
            for s in MODEL['lessons'][lid]['steps']:
                self.assertIn('id="' + s['id'] + '"', html)

    def test_lesson_static_full_text(self):
        """样课页静态 HTML 含全文（含 answer-zone 答案区）：无脚本也可读。"""
        html = self.pages()["lessons/run-and-bindings.html"]
        self.assertIn("answer-zone", html)
        # 关键讲解与解析全文在 HTML 中（不依赖 JS 渲染）
        for needle in ["绑定快照", "先取旧值加一，再重新绑定",
                       "先预测，再点开展开实际输出",
                       "中间结果不会自动重算",
                       "口头检查：改了 copies，之前计算过的 total 为什么不会自己变化？"]:
            self.assertIn(needle, html, f"样课页缺静态文本: {needle!r}")

    def test_quiz_data_matches_yaml(self):
        """quiz 块 data-correct-option 与 YAML 的 correctOptionId 一致。"""
        lesson_yaml = yaml.safe_load(
            (REPO_ROOT / "content" / "lessons" / "run-and-bindings.yaml")
            .read_text(encoding="utf-8"))
        expected = {}
        for step in lesson_yaml["steps"]:
            if step["type"] == "quiz":
                expected[step["questionId"]] = step["correctOptionId"]
        html = self.pages()["lessons/run-and-bindings.html"]
        found = dict(DATA_CORRECT_RE.findall(html))
        self.assertEqual(set(found), set(expected),
                         f"quiz 块与 YAML 题目集合不一致: {found} vs {expected}")
        for qid, correct in expected.items():
            self.assertEqual(found[qid], correct,
                             f"题目 {qid} 的 data-correct-option 与 YAML 不一致")

    def test_step_anchor_ids_present(self):
        """样课 7 个步骤的锚点 id 都在页面中。"""
        html = self.pages()["lessons/run-and-bindings.html"]
        ids = set(ID_RE.findall(html))
        for sid in ("s-goal", "s-mechanism", "s-predict", "s-misconception",
                    "s-quiz-1", "s-quiz-2", "s-recap"):
            self.assertIn(sid, ids, f"样课页缺步骤锚点 id={sid}")


class TestSizeBudgets(BuildBase):
    def test_html_budgets(self):
        """每页 HTML ≤ 60 KiB。"""
        for rel, html in self.pages().items():
            size = (self.dist / rel).stat().st_size
            self.assertLessEqual(
                size, HTML_BUDGET,
                f"{rel} 体积 {size/1024:.1f} KiB 超过 60 KiB 预算")

    def test_js_budget(self):
        """reader.js 哈希产物 ≤ 30 KiB。"""
        js = list((self.dist / "assets").glob("reader.*.js"))
        self.assertEqual(len(js), 1)
        size = js[0].stat().st_size
        self.assertLessEqual(size, JS_BUDGET,
                             f"JS 体积 {size/1024:.1f} KiB 超过 30 KiB 预算")

    def test_css_budget(self):
        """styles.css 哈希产物 ≤ 10 KiB。"""
        css = list((self.dist / "assets").glob("styles.*.css"))
        self.assertEqual(len(css), 1)
        size = css[0].stat().st_size
        self.assertLessEqual(size, CSS_BUDGET,
                             f"CSS 体积 {size/1024:.1f} KiB 超过 10 KiB 预算")


class TestBasePathPrefix(unittest.TestCase):
    """--base-path /myrepo/：内链、资源、PRL_CONFIG 均带前缀。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        rc, cls.dist = build_to(cls._tmp.name, base_path="/myrepo/")
        assert rc == 0, "basePath=/myrepo/ 构建失败"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _pages(self):
        out = {}
        for p in self.dist.rglob("*.html"):
            out[p.relative_to(self.dist).as_posix()] = p.read_text(encoding="utf-8")
        return out

    def test_links_carry_prefix(self):
        """所有以 / 开头的内链都带 /myrepo/ 前缀（无硬编码根路径）。"""
        for rel, html in self._pages().items():
            for kind, pattern in (("href", HREF_RE), ("src", SRC_RE)):
                for ref in pattern.findall(html):
                    if not ref or ref.startswith("#") or re.match(r"https?://", ref):
                        continue
                    if ref.startswith("/"):
                        self.assertTrue(
                            ref.startswith("/myrepo/"),
                            f"{rel}: {kind}={ref!r} 丢失 /myrepo/ 前缀（疑似硬编码根路径）")

    def test_prl_config_carries_prefix(self):
        """PRL_CONFIG 中的 basePath 为 /myrepo/。"""
        for rel, html in self._pages().items():
            self.assertIn('"basePath":"/myrepo/"', html,
                          f"{rel}: PRL_CONFIG 缺 /myrepo/ 前缀")

    def test_assets_still_resolve(self):
        """带前缀的资源引用对应真实文件。"""
        for rel, html in self._pages().items():
            for ref in SRC_RE.findall(html) + HREF_RE.findall(html):
                if ref.startswith("/myrepo/assets/"):
                    target = self.dist / ref[len("/myrepo/"):]
                    self.assertTrue(target.is_file(),
                                    f"{rel}: 资源 {ref} 不存在")


class TestWorkflowYaml(unittest.TestCase):
    def test_workflow_syntax_valid_and_has_test_job(self):
        """pages.yml 经 yaml.safe_load 合法，且包含 test job。"""
        text = (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8")
        wf = yaml.safe_load(text)
        self.assertIsInstance(wf, dict)
        jobs = wf.get("jobs") or {}
        self.assertIn("test", jobs, "workflow 应包含 test job")
        steps = jobs["test"].get("steps") or []
        runs = " ".join(str(s.get("run", "")) for s in steps)
        self.assertIn("python tools/audit_v1.py", runs)
        self.assertIn("npm ci", runs)
        self.assertIn("playwright install --with-deps chromium", runs)
        self.assertEqual(jobs["build"]["needs"], "test")
        self.assertEqual(jobs["deploy"]["needs"], "build")
        self.assertEqual(jobs["deploy"]["permissions"], {"pages": "write", "id-token": "write"})
        self.assertIn("pull_request", wf.get("on", wf.get(True)))


class TestBuildGuards(unittest.TestCase):
    def test_broken_src_wrong_base_and_missing_anchor_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for source in ['<script src="/repo/missing.js"></script>',
                           '<a href="/wrong.html">bad</a>',
                           '<a href="#fake">bad</a><p data-id="fake"></p>']:
                (root/'index.html').write_text(source)
                self.assertTrue(builder.check_links(root, '/repo/'), source)

    def test_source_cannot_be_used_as_output_directory(self):
        for target in [REPO_ROOT, REPO_ROOT/'content', REPO_ROOT/'assets']:
            self.assertEqual(builder.main(['--out', str(target)]), 1)


if __name__ == "__main__":
    unittest.main()
