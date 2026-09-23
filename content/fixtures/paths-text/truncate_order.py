import tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "report.txt"
    out.write_text("旧报告")  # 准备旧报告
    try:  # 错误顺序：先开输出，再读输入
        with out.open("w", encoding="utf-8") as f:
            text = Path(tmp, "nope.txt").read_text(encoding="utf-8")
            f.write(text)
    except FileNotFoundError:
        print("读取失败")
    print("旧报告还在：", out.read_text(encoding="utf-8") == "旧报告")
