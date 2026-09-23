"""P4 参考：纯函数，可独立导入、独立测试。"""


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
    for count in counts.values():
        total += count
    lines = ["总词数：" + str(total), "不同词数：" + str(len(counts))]
    ordered = sorted(counts.items(), key=count_key, reverse=True)
    for name, count in ordered:
        lines.append(name + ": " + str(count))
    return "\n".join(lines) + "\n"
