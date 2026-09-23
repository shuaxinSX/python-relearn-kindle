def parse_count(raw):
    return int(raw)

try:
    parse_count("bad")
except ValueError as exc:
    print(type(exc).__name__)
