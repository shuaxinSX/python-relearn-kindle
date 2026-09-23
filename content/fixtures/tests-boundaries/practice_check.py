"""P4 固定内容测试：12 条全部用 assert 覆盖，通过则打印 ALL ACCEPTANCE OK。"""

import io
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

FIXDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(FIXDIR))
from reference_main import main
from reference_solution import count_words, format_report

FIXED_TEXT = "Python python\nSQL api SQL\n\nAPI python\n"
FIXED_REPORT = "总词数：7\n不同词数：3\npython: 3\nsql: 2\napi: 2\n"

# 1. 普通样例
counts = count_words(FIXED_TEXT)
assert counts == {"python": 3, "sql": 2, "api": 2}, counts
assert format_report(counts) == FIXED_REPORT

# 2/3. 空文本与仅空白
assert count_words("") == {}
assert format_report({}) == "总词数：0\n不同词数：0\n"
assert count_words(" \n\t ") == {}
assert format_report(count_words(" \n\t ")) == "总词数：0\n不同词数：0\n"

# 4. 单词
assert count_words("Python") == {"python": 1}
assert format_report({"python": 1}) == "总词数：1\n不同词数：1\npython: 1\n"

# 5. 重复同一词
assert count_words("API api API") == {"api": 3}
assert format_report({"api": 3}) == "总词数：3\n不同词数：1\napi: 3\n"

# 6. 同频按首次出现顺序
two = count_words("sql api")
assert two == {"sql": 1, "api": 1}, two
assert format_report(two) == "总词数：2\n不同词数：2\nsql: 1\napi: 1\n"

# 7. 中文词
cn = count_words("数据 data 数据")
assert cn == {"数据": 2, "data": 1}, cn
assert format_report(cn) == "总词数：3\n不同词数：2\n数据: 2\ndata: 1\n"

# 8. 标点不删除
punct = count_words("Python, python")
assert punct == {"python,": 1, "python": 1}, punct

# 9. 连续调用不累积
assert count_words(FIXED_TEXT) == count_words(FIXED_TEXT) == counts

# 10. format_report 不修改 counts
before = dict(counts)
order_before = list(counts)
format_report(counts)
assert dict(counts) == before and list(counts) == order_before

# 11. 直接 import 无副作用：无输出、不产生文件
before_files = set(p.name for p in FIXDIR.iterdir())
proc = subprocess.run(
    [sys.executable, "-c", "import reference_solution"],
    cwd=FIXDIR, capture_output=True, timeout=30)
assert proc.returncode == 0, proc.stderr
assert proc.stdout == b"", proc.stdout
assert set(p.name for p in FIXDIR.iterdir()) == before_files

# 12. 运行入口两次：报告相同，不追加
with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / "input.txt"
    out = Path(tmp) / "report.txt"
    src.write_text(FIXED_TEXT, encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(str(src), str(out))
    assert "报告已生成" in buf.getvalue()
    first = out.read_bytes()
    assert first.decode("utf-8") == FIXED_REPORT
    with redirect_stdout(io.StringIO()):
        main(str(src), str(out))
    assert out.read_bytes() == first

print("ALL ACCEPTANCE OK")
