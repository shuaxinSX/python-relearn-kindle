def minutes_key(record):
    return record["minutes"]

records = [{"name": "a", "minutes": 30},
           {"name": "b", "minutes": 10}]
ordered = sorted(records,
                 key=minutes_key)
print([r["name"] for r in ordered])
print([r["name"] for r in records])
print(records.sort(key=minutes_key))
