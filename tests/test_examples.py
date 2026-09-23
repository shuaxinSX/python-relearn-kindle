#!/usr/bin/env python3
"""fixtures 真实运行测试。

遍历 content/fixtures/<lessonId>/*.py，用 sys.executable
实际运行，断言：退出码 0，且 stdout 与同名 .expected.txt 逐字节一致。
（开发规格 §5.3：所有声称可运行的示例必须验证实际输出）
"""

import subprocess
import sys
import tempfile
import shutil
import os
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_ROOT = REPO_ROOT / "content" / "fixtures"


def iter_scripts():
    for lesson_dir in sorted(FIXTURES_ROOT.iterdir()):
        if not lesson_dir.is_dir():
            continue
        for script in sorted(lesson_dir.glob("*.py")):
            yield lesson_dir.name, script


class TestFixturesRun(unittest.TestCase):
    def test_fixture_outputs_match_expected(self):
        scripts = list(iter_scripts())
        self.assertTrue(scripts, f"fixtures 目录为空: {FIXTURES_ROOT}")
        for lesson_id, script in scripts:
            with self.subTest(lesson=lesson_id, script=script.name):
                expected_path = script.with_suffix("").with_name(
                    script.stem + ".expected.txt")
                self.assertTrue(
                    expected_path.is_file(),
                    f"{lesson_id}/{script.name} 缺同名 .expected.txt")
                expected = expected_path.read_bytes()
                # Every fixture gets a disposable working directory. No file
                # example runs in the checkout or touches user input/report files.
                with tempfile.TemporaryDirectory() as tmp:
                    work = Path(tmp) / lesson_id
                    shutil.copytree(script.parent, work, ignore=shutil.ignore_patterns('__pycache__'))
                    proc = subprocess.run(
                        [sys.executable, '-B', str(work / script.name)], cwd=work,
                        env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'},
                        capture_output=True, timeout=30)
                self.assertEqual(
                    proc.returncode, 0,
                    f"{lesson_id}/{script.name} 退出码 {proc.returncode}，"
                    f"stderr={proc.stderr!r}")
                self.assertEqual(
                    proc.stdout, expected,
                    f"{lesson_id}/{script.name} 输出与 {expected_path.name} "
                    f"逐字节不一致：实际={proc.stdout!r} 期望={expected!r}")
                self.assertEqual(proc.stderr, b'', f'{lesson_id}/{script.name}: unexpected stderr')

    def test_fixture_pairs_core_81_plus_m0_12_and_no_orphan_expected(self):
        # Core/M0 分口径：核心课 81 对 + M0 12 对 = 93。
        scripts = list(iter_scripts())
        core = [s for s in scripts if not s[0].startswith('m0-')]
        m0 = [s for s in scripts if s[0].startswith('m0-')]
        self.assertEqual(len(core), 81, 'V1 core fixture inventory changed; review the full inventory')
        self.assertEqual(len(m0), 12, 'M0 fixture inventory changed; review the full inventory')
        self.assertEqual(len(scripts), 93)
        expected = {p.with_suffix('.expected.txt') for _, p in scripts}
        self.assertEqual(expected, set(FIXTURES_ROOT.rglob('*.expected.txt')))


if __name__ == "__main__":
    unittest.main()
