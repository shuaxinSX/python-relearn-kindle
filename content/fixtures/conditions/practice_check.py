#!/usr/bin/env python3
"""P1 验收检查：用参考解法脚本本身覆盖全部 7 行固定验收。

做法：读取 p1_solution.py，把开头的四个输入赋值替换成每组
验收输入后执行，断言输出与预期逐字节一致。
"""
import io
from contextlib import redirect_stdout
from pathlib import Path

SOLUTION = Path(__file__).with_name("p1_solution.py")
SOURCE = SOLUTION.read_text(encoding="utf-8")

INPUT_BLOCK = (
    'raw_title = " Python Basics "\n'
    'raw_count = "3"\n'
    'unit_price = 20\n'
    'is_member = False\n'
)

assert INPUT_BLOCK in SOURCE, "p1_solution.py 开头输入块格式变了，请同步更新本脚本"


def run_case(raw_title, raw_count, is_member):
    header = (
        f"raw_title = {raw_title!r}\n"
        f"raw_count = {raw_count!r}\n"
        "unit_price = 20\n"
        f"is_member = {is_member!r}\n"
    )
    code = header + SOURCE.split(INPUT_BLOCK, 1)[1]
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(code, str(SOLUTION), "exec"), {"__name__": "__main__"})
    return buf.getvalue()


CASES = [
    # (raw_title, raw_count, is_member, 期望输出)
    (" Python Basics ", "3", False,
     "资料：python basics\n份数：3\n应付：68.00 元\n"),
    (" Python Basics ", "4", False,
     "资料：python basics\n份数：4\n应付：88.00 元\n"),
    (" Python Basics ", "5", False,
     "资料：python basics\n份数：5\n应付：100.00 元\n"),
    (" Python Basics ", "3", True,
     "资料：python basics\n份数：3\n应付：60.00 元\n"),
    (" Python Basics ", "0", False,
     "资料：python basics\n份数：0\n应付：0.00 元\n"),
    (" Python Basics ", "-1", False,
     "输入无效\n"),
    ("   ", "3", False,
     "输入无效\n"),
]

for raw_title, raw_count, is_member, expected in CASES:
    actual = run_case(raw_title, raw_count, is_member)
    assert actual == expected, (
        f"验收失败: raw_title={raw_title!r} raw_count={raw_count!r} "
        f"is_member={is_member!r}\n实际={actual!r}\n期望={expected!r}"
    )

print("ALL ACCEPTANCE OK")
