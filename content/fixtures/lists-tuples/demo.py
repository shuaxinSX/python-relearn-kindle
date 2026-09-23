raw = [" INFO ", "", "ERROR"]
cleaned = []
for item in raw:
    name = item.strip().lower()
    if name != "":
        cleaned.append(name)
print(cleaned)
