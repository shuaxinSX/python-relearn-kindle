counts = {}
for tag in ["python", "sql", "python"]:
    counts[tag] = counts.get(tag, 0) + 1
print(counts["python"], counts["sql"])
