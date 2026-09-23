"""P3 七行固定验收检查：全部用 assert，末尾打印 ALL ACCEPTANCE OK。"""
import io
from contextlib import redirect_stdout

with redirect_stdout(io.StringIO()):
    import solution

# 验收 1：普通样例（sql 在 api 前，两个 python 都保留）
ordered = sorted(solution.clean_records(solution.records),
                 key=solution.minutes_key)
got = [(r["name"], r["minutes"]) for r in ordered]
assert got == [("cli", 0), ("python", 15), ("sql", 20),
               ("api", 20), ("python", 30)], got

# 验收 2：空输入
assert solution.clean_records([]) == []

# 验收 3：单条 name 非空、minutes 为 0 的记录保留（名称已规范化）
only_zero = [{"name": "CLI", "minutes": 0}]
assert solution.clean_records(only_zero) == [{"name": "cli", "minutes": 0}]

# 验收 4：全部名称为空白或分钟数为负，无有效记录
bad = [{"name": "   ", "minutes": 5}, {"name": "x", "minutes": -2}]
assert solution.clean_records(bad) == []

# 验收 5：处理前后原 records 不被修改（前后对照）
before = [(r["name"], r["minutes"]) for r in solution.records]
solution.clean_records(solution.records)
after = [(r["name"], r["minutes"]) for r in solution.records]
assert before == after == [
    (" Python ", 30), ("", 10), ("SQL", 20), ("python", 15),
    ("API", 20), ("CLI", 0), ("BAD", -1)], after

# 验收 6：同一输入连续运行两次清洗，结果相同且不累积
first = solution.clean_records(solution.records)
second = solution.clean_records(solution.records)
assert first == second
assert len(first) == 5

# 验收 7：修改清洗结果字典的 name，原记录不受影响
cleaned = solution.clean_records(solution.records)
cleaned[0]["name"] = "HACKED"
assert solution.records[0]["name"] == " Python "
assert all(r["name"] != "HACKED" for r in solution.records)

# 函数契约抽查
assert solution.normalize_name(" Python ") == "python"
assert solution.clean_record({"name": " ", "minutes": 1}) is None
assert solution.minutes_key({"name": "x", "minutes": 7}) == 7

print("ALL ACCEPTANCE OK")
