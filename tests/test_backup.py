#!/usr/bin/env python3
"""备份校验测试：用 node 真实加载 assets/reader.js 的
validateBackupText（导出的 module.exports），覆盖合法与各类非法输入。
node 不可用时跳过。
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER = Path(__file__).resolve().parent / "backup_driver.js"

HAS_NODE = shutil.which("node") is not None


@unittest.skipIf(not HAS_NODE, "node 不可用，跳过备份校验测试")
class TestBackupValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proc = subprocess.run(["node", str(DRIVER)],
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"备份驱动执行失败：{proc.stderr}"
        cls.results = {r["name"]: r for r in json.loads(proc.stdout)}

    def _assert_pass(self, name):
        self.assertIn(name, self.results, f"驱动未报告用例 {name}")
        self.assertTrue(self.results[name].get("pass"),
                        f"备份校验用例 {name} 未通过：{self.results[name]}")

    def test_valid_backup_ok_with_preview_counts(self):
        """合法备份 ok，preview.read / preview.review 计数正确。"""
        self._assert_pass("valid")

    def test_too_large(self):
        """超 128KiB → too-large。"""
        self._assert_pass("too-large")

    def test_invalid_json(self):
        """坏 JSON → invalid-json。"""
        self._assert_pass("invalid-json")

    def test_unsafe_keys(self):
        """__proto__ 注入 → unsafe-keys。"""
        self._assert_pass("unsafe-keys")

    def test_unknown_version(self):
        """schemaVersion=2 → unknown-version。"""
        self._assert_pass("unknown-version")

    def test_course_mismatch(self):
        """courseId 不符 → course-mismatch。"""
        self._assert_pass("course-mismatch")

    def test_bad_fields_font_size(self):
        """fontSize 非法 → bad-fields。"""
        self._assert_pass("bad-fields-fontsize")

    def test_bad_fields_attempts(self):
        """attempts 负数 → bad-fields。"""
        self._assert_pass("bad-fields-attempts")


if __name__ == "__main__":
    unittest.main()
