"""P2 全部 5 行固定验收的内部检查：用参考解法的脚本本身逐条验证。"""

cases = [
    # (输入, 期望 (valid, ignored, unique顺序, counts))
    (
        [" Python ", "SQL", "python", "", "API", " sql ", "   ", "API"],
        (6, 2, ["python", "sql", "api"], {"python": 2, "sql": 2, "api": 2}),
    ),
    ([], (0, 0, [], {})),
    (["", "   "], (0, 2, [], {})),
    (["API", " api ", "api"], (3, 0, ["api"], {"api": 3})),
    (["SQL", "Python"], (2, 0, ["sql", "python"], {"sql": 1, "python": 1})),
]

for raw_tags, (want_valid, want_ignored, want_unique, want_counts) in cases:
    import ast
    import io
    from contextlib import redirect_stdout
    from pathlib import Path
    tree = ast.parse(Path(__file__).with_name("practice.py").read_text())
    tree.body[0].value = ast.parse(repr(raw_tags), mode="eval").body
    scope = {}
    with redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), "practice.py", "exec"), scope)
    valid, ignored = scope["valid"], scope["ignored"]
    unique, counts = scope["unique"], scope["counts"]
    assert valid == want_valid, (raw_tags, valid, want_valid)
    assert ignored == want_ignored, (raw_tags, ignored, want_ignored)
    assert unique == want_unique, (raw_tags, unique, want_unique)
    assert counts == want_counts, (raw_tags, counts, want_counts)

print("ALL ACCEPTANCE OK")
