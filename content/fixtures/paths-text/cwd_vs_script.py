import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    project = Path(tmp) / "project"
    project.mkdir()
    (project / "input.txt").write_text("hi", encoding="utf-8")
    os.chdir(tmp)  # 工作目录是项目目录的上一级
    print(Path("input.txt").exists())  # 相对路径相对 cwd
    print((project / "input.txt").exists())  # 明确的位置才稳定
