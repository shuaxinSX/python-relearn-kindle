assert 1 + 1 == 2  # 约定成立：安静通过
try:
    assert 1 + 1 == 3, "约定：1+1 等于 2"
except AssertionError as exc:
    print(type(exc).__name__)
print("done")
