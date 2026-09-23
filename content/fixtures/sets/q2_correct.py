seen = set()
unique = []
counts = {}
for tag in ["python", "sql", "python"]:
    counts[tag] = counts.get(tag, 0) + 1
    if tag not in seen:
        seen.add(tag)
        unique.append(tag)
print(unique)
for tag in unique:
    print(tag, counts[tag])
