def normalize_name(text):
    return text.strip().lower()


def show_name(text):
    print(text.strip().lower())


print(normalize_name(" Python "))
got = show_name(" SQL ")
print(got)
