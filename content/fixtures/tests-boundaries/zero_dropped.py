def keep_names(records):
    kept = []
    for record in records:
        if record["minutes"] > 0:
            kept.append(record["name"])
    return kept

zero = [{"name": "CLI", "minutes": 0}]
print(keep_names(zero))
normal = [{"name": "A", "minutes": 10}]
print(keep_names(normal))
