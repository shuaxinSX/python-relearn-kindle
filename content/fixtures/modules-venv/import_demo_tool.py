"""工具模块：顶层语句在导入时执行。"""

print("loaded")


def count_words(text):
    counts = {}
    for word in text.lower().split():
        counts[word] = counts.get(word, 0) + 1
    return counts


def main():
    print("report")


if __name__ == "__main__":
    main()
