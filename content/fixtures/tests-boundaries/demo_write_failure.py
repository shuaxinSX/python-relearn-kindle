"""文件失败路径演示 3：写入失败（report.txt 预先建成目录来模拟）。"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_main import main

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / "input.txt"
    out = Path(tmp) / "report.txt"
    src.write_text("Python python\n", encoding="utf-8")
    out.mkdir()  # 把输出路径预先建成目录，模拟写入失败
    main(str(src), str(out))
    print("输出仍是目录：" + str(out.is_dir()))
