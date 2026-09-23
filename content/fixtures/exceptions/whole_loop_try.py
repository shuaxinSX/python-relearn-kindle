results = []
try:
    for raw in ["0", "bad", "5"]:
        results.append(int(raw))
except ValueError:
    pass
print(results)
