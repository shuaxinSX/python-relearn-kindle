results = []
for raw in ["0", "bad", "5"]:
    try:
        results.append(int(raw))
    except ValueError:
        results.append(0)
print(results)
