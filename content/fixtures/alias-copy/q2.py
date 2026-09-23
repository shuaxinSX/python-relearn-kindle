a = [[1], [2]]
b = a.copy()
b[0].append(9)
print(a)
print(a is b)
