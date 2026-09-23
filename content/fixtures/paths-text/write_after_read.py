import tempfile
from pathlib import Path

src = Path(__file__).parent / "sample_input.txt"
with src.open(encoding="utf-8") as f:
    text = f.read()
words = text.lower().split()
lines = ["总词数：" + str(len(words))]
lines.append("python：" + str(words.count("python")))
report = "\n".join(lines) + "\n"
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "report.txt"
    with out.open("w", encoding="utf-8") as f:  # 成功后才打开输出
        f.write(report)
    print(out.read_text(encoding="utf-8"), end="")
