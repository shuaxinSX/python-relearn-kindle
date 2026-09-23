def count_words(text):
    counts = {}
    for word in text.lower().split():
        counts[word] = counts.get(word, 0) + 1
    return counts

def count_key(item):
    name, count = item
    return count

def format_report(counts):
    total = 0
    for name, count in counts.items():
        total = total + count
    lines = ["总词数：" + str(total)]
    lines.append("不同词数：" + str(len(counts)))
    ordered = sorted(counts.items(), key=count_key, reverse=True)
    for name, count in ordered:
        lines.append(name + ": " + str(count))
    return "\n".join(lines) + "\n"
