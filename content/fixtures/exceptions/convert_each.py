results = []
bad_items = []
for raw in ["0", "bad", "5"]:
    try:
        results.append(int(raw))
    except ValueError:
        bad_items.append(raw)
print(results)
print(bad_items)
