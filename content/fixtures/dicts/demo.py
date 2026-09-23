counts = {}
for tag in ["python", "sql", "python"]:
    old = counts.get(tag, 0)
    counts[tag] = old + 1
print(counts)
