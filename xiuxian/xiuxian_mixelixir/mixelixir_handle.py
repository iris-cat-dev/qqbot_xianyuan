import random



upper_limit = 10

# 解的集合
solutions = []

itemA = random.randint(1, 9)
itemB = random.randint(1, 9)
itemC = random.randint(1, 9)
itemD = random.randint(1, 9)

# 穷举所有可能的解
for A in range(1, upper_limit):
    for B in range(1, upper_limit):
        for C in range(1, upper_limit):
            for D in range(1, upper_limit):
                if itemA * A - itemB * B + itemC * C - itemD * D == 0:
                    solutions.append((A, B, C, D))

# 打印所有解
for solution in solutions:
    print(f"{itemA}x{solution[0]}, {itemB}x{solution[1]}, {itemC}x{solution[2]}, {itemD}x{solution[3]}")

