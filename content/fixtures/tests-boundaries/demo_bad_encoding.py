"""文件失败路径演示 2：无效 UTF-8。专用临时目录，输出确定。"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_main import main

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / "input.txt"
    out = Path(tmp) / "report.txt"
    src.write_bytes(b"\xff\xfe\xff not utf-8 \x80")
    out.write_text("旧报告\n", encoding="utf-8")
    main(str(src), str(out))
    print("旧报告保留：" + str(out.read_text(encoding="utf-8") == "旧报告\n"))
