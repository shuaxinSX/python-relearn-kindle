from pathlib import Path

try:
    with Path("一定不存在的输入文件.txt").open(encoding="utf-8") as f:
        f.read()
except FileNotFoundError as exc:
    print(type(exc).__name__)
