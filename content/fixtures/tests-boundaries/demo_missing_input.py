"""文件失败路径演示 1：输入缺失。专用临时目录，输出确定。"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_main import main

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "report.txt"
    main(str(Path(tmp) / "input.txt"), str(out))  # input.txt 不存在
    print("输出文件已生成：" + str(out.exists()))
