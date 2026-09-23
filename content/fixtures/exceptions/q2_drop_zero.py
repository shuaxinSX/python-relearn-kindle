results = []
for raw in ["0", "bad", "5"]:
    try:
        value = int(raw)
    except ValueError:
        continue
    if value:
        results.append(value)
print(results)
