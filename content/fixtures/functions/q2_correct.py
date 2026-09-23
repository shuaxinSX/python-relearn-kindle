def clean_names(names):
    result = []
    for name in names:
        result.append(name.strip().lower())
    return result


print(clean_names([" A ", "B"]))
print(clean_names([]))
