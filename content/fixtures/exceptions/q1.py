def parse_count(raw):
    return int(raw)

try:
    count = parse_count("bad")
    print("数量：", count)
except ValueError as exc:
    print(type(exc).__name__)
