import random

# 可能的格子类型
TILE_TYPES = ['Grass', 'Water', 'Mountain']

# 地图大小
MAP_WIDTH = 10
MAP_HEIGHT = 10


# 创建初始的波函数地图，每个格子包含所有可能的类型
def create_initial_wave():
    return [[list(TILE_TYPES) for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]


# 检查格子是否坍塌（即是否只剩下一种可能）
def is_collapsed(wave, x, y):
    return len(wave[y][x]) == 1


# 波函数坍塌的主要函数
def observe(wave):
    non_collapsed_cells = [(x, y) for y in range(MAP_HEIGHT) for x in range(MAP_WIDTH) if not is_collapsed(wave, x, y)]

    # 如果所有格子都坍塌了，返回True
    if not non_collapsed_cells:
        return True

    # 随机选择一个未坍塌的格子来坍塌
    x, y = random.choice(non_collapsed_cells)
    wave[y][x] = [random.choice(wave[y][x])]
    return False

# 根据坍塌的格子更新周围的波函数格子
def propagate(wave):
    changes = [(x, y) for x in range(MAP_WIDTH) for y in range(MAP_HEIGHT) if is_collapsed(wave, x, y)]

    while changes:
        x, y = changes.pop()
        collapsed_type = wave[y][x][0]

        # 查看四个方向的格子
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT and not is_collapsed(wave, nx, ny):
                # 移除与已坍塌邻居格子不相容的类型
                original = set(wave[ny][nx])
                wave[ny][nx] = [t for t in wave[ny][nx] if t != collapsed_type]  # 假设相邻格子不能为相同类型
                if set(wave[ny][nx]) != original:
                    changes.append((nx, ny))


# 输出最终地图
def output_wave(wave):
    tile_map = [[' ' for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if is_collapsed(wave, x, y):
                tile_map[y][x] = wave[y][x][0]

    return tile_map

def generate_map():
    wave = create_initial_wave()
    while True:
        finished = observe(wave)
        if finished:
            break
        propagate(wave)
    output_wave(wave)

# 打印地图结果
def print_map(tile_map):
    for row in tile_map:
        print(' '.join(row))

# 主程序入口
if __name__ == "__main__":
    wave = create_initial_wave()   # 创建初始波函数地图
    done = False
    while not done:
        done = observe(wave)      # 坍塌波函数
        propagate(wave)           # 传播坍塌结果
    tile_map = output_wave(wave)  # 获取最终的地图
    print_map(tile_map)           # 打印地图
