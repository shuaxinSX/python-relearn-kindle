seen = set()
unique = []
for tag in ["python", "sql", "python"]:
    if tag not in seen:
        seen.add(tag)
        unique.append(tag)
print(unique)
print(len(seen))
