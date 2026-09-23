from pathlib import Path

# 脚本所在目录，不随工作目录变
path = Path(__file__).parent / "sample_input.txt"
with path.open(encoding="utf-8") as f:
    text = f.read()
words = text.lower().split()
print(len(words))
print(words.count("python"))
