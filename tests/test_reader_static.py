#!/usr/bin/env python3
"""reader.js 静态检查：node --check 语法校验、ES5 启发式扫描、
体积上限、无 localStorage.clear()。node 不可用时相关用例跳过。
"""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
READER_JS = REPO_ROOT / "assets" / "reader.js"
STYLES_CSS = REPO_ROOT / "assets" / "styles.css"

JS_BUDGET = 30 * 1024    # 30720
CSS_BUDGET = 10 * 1024   # 10240

HAS_NODE = shutil.which("node") is not None

# ES5 以外的语法/API 启发式（注释与字符串已先行剥离，见 _strip）
ES5_FORBIDDEN = [
    (r"\b(let|const)\b", "let/const"),
    (r"=>", "箭头函数"),
    ("`", "模板字符串/反引号"),
    (r"\bclass\b", "class"),
    (r"\bfetch\s*\(", "fetch("),
    (r"\bPromise\b", "Promise"),
    (r"\basync\b", "async"),
    (r"\bawait\b", "await"),
    (r"(?m)^\s*import\s", "行首 import"),
    (r"(?m)^\s*export\s", "行首 export"),
]


def _strip_comments_and_strings(src):
    """剥离 // 与 /* */ 注释及单/双引号字符串（ES5 源码用，无模板字符串）。"""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c in ("'", '"'):
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c:
                    break
                j += 1
            i = j + 1
            continue
        # 正则字面量可能含特殊字符，保守起见保留原样（ES5 允许）
        out.append(c)
        i += 1
    return "".join(out)


class TestReaderStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = READER_JS.read_text(encoding="utf-8")
        cls.code = _strip_comments_and_strings(cls.source)

    @unittest.skipIf(not HAS_NODE, "node 不可用，跳过 node --check")
    def test_node_check_passes(self):
        """node --check assets/reader.js 通过。"""
        proc = subprocess.run(["node", "--check", str(READER_JS)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0,
                         f"node --check 失败：{proc.stderr}")

    def test_es5_heuristics_zero_hits(self):
        """ES5 启发式扫描零命中。"""
        hits = []
        for pattern, label in ES5_FORBIDDEN:
            for m in re.finditer(pattern, self.code):
                line = self.code.count("\n", 0, m.start()) + 1
                hits.append(f"第{line}行: {label}（{m.group(0)!r}）")
                break
        self.assertEqual(hits, [], "ES5 启发式扫描命中：\n" + "\n".join(hits))

    def test_js_size_budget(self):
        """reader.js ≤ 30720 字节（30 KiB）。"""
        size = READER_JS.stat().st_size
        self.assertLessEqual(size, JS_BUDGET,
                             f"reader.js {size} 字节超过 30720 预算")

    def test_css_size_budget(self):
        """styles.css ≤ 10240 字节（10 KiB）。"""
        size = STYLES_CSS.stat().st_size
        self.assertLessEqual(size, CSS_BUDGET,
                             f"styles.css {size} 字节超过 10240 预算")

    def test_no_localstorage_clear(self):
        """源码无 localStorage.clear()（规格 §7 禁止）。"""
        self.assertNotIn("localStorage.clear()", self.source,
                         "reader.js 不得调用 localStorage.clear()")


if __name__ == "__main__":
    unittest.main()
