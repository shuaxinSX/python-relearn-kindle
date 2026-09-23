raw = [" A ", "", "B"]
cleaned = []
for x in raw:
    if x.strip():
        cleaned.append(x.strip().lower())
short = [x.strip().lower()
         for x in raw if x.strip()]
print(cleaned, short)
