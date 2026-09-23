raw_tags = [
    " Python ", "SQL", "python", "",
    "API", " sql ", "   ", "API",
]

seen = set()    # 已经出现过的规范标签，只判重
unique = []     # 首次出现顺序，只保序
counts = {}     # 每个标签的原始次数，只计数
valid = 0       # 有效记录数
ignored = 0     # 忽略记录数

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

print(f"有效记录：{valid}")
print(f"不同标签：{len(unique)}")
print(f"忽略记录：{ignored}")
for tag in unique:
    print(f"{tag}: {counts[tag]}")
