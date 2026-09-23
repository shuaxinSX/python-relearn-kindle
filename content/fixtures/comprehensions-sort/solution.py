def normalize_name(text):
    return text.strip().lower()


def clean_record(record):
    name = normalize_name(record["name"])
    minutes = record["minutes"]
    if name == "" or minutes < 0:
        return None
    return {"name": name, "minutes": minutes}


def clean_records(records):
    result = []
    for record in records:
        cleaned = clean_record(record)
        if cleaned is not None:
            result.append(cleaned)
    return result


def minutes_key(record):
    return record["minutes"]


records = [
    {"name": " Python ", "minutes": 30},
    {"name": "", "minutes": 10},
    {"name": "SQL", "minutes": 20},
    {"name": "python", "minutes": 15},
    {"name": "API", "minutes": 20},
    {"name": "CLI", "minutes": 0},
    {"name": "BAD", "minutes": -1},
]

cleaned = clean_records(records)
ordered = sorted(cleaned, key=minutes_key)

print(f"有效记录：{len(ordered)}")
for item in ordered:
    name = item["name"]
    minutes = item["minutes"]
    print(f"{name}: {minutes}")
