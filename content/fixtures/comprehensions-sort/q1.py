raw = [" A ", "", "B"]
cleaned = []
for x in raw:
    if x.strip():
        cleaned.append(x.strip().lower())
print(cleaned)
