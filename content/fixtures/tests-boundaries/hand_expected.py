def count_words(text):
    counts = {}
    for word in text.lower().split():
        counts[word] = counts.get(word, 0) + 1
    return counts

expected = {"python": 2}  # 独立手算
result = count_words("Python python")
assert result == expected
print("ok")
