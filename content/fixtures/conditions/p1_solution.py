# P1 参考解法：生成资料费用说明（标准样例输入）
raw_title = " Python Basics "
raw_count = "3"
unit_price = 20
is_member = False

name = raw_title.strip().lower()
count = int(raw_count)

if name == "" or count < 0:
    print("输入无效")
else:
    materials = count * unit_price
    if count == 0:
        total = 0
    elif materials >= 100 or is_member:
        total = materials
    else:
        total = materials + 8
    print("资料：" + name)
    print("份数：" + str(count))
    print(f"应付：{total:.2f} 元")
