"""P2 全部 5 行固定验收的内部检查：用参考解法的同一逻辑逐条验证。"""

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
    seen = set()
    unique = []
    counts = {}
    valid = 0
    ignored = 0
    for raw in raw_tags:
        tag = raw.strip().lower()
        if tag == "":
            ignored = ignored + 1
            continue
        valid = valid + 1
        counts[tag] = counts.get(tag, 0) + 1
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    assert valid == want_valid, (raw_tags, valid, want_valid)
    assert ignored == want_ignored, (raw_tags, ignored, want_ignored)
    assert unique == want_unique, (raw_tags, unique, want_unique)
    assert counts == want_counts, (raw_tags, counts, want_counts)

print("ALL ACCEPTANCE OK")
