def normalize_name(text):
    return text.strip().lower()


cleaned = normalize_name(" Python ")
print(cleaned)
print(normalize_name("API"))
