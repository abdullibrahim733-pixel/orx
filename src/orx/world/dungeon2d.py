"""2D dungeon generator with traps, secrets, and rooms."""

from __future__ import annotations

import random
from orx.map.world import WorldMap
from orx import constants as C


class WorldMap2D(WorldMap):
    def __init__(self, grid, spawn, exit_pos, enemy_spawns=None):
        super().__init__(grid, spawn, enemy_spawns)
        self.exit_pos = exit_pos


def generate_dungeon_2d(seed: int | None = None, level: int = 1) -> WorldMap2D:
    if seed is not None:
        random.seed(seed)

    size = C.MAP_WIDTH
    if level > 5:
        size = 28
    if level > 10:
        size = 32
    if level > 15:
        size = 36
    if level > 20:
        size = 40

    grid = [[1] * size for _ in range(size)]

    rooms = []
    min_room = 3 + level // 5
    max_room = 6 + level // 5
    target_rooms = min(8 + level // 3, 18)

    for _ in range(target_rooms * 15):
        rw = random.randint(min_room, max_room)
        rh = random.randint(min_room, max_room)
        rx = random.randint(1, size - rw - 2)
        ry = random.randint(1, size - rh - 2)

        overlaps = False
        padding = 1
        for ox, oy, ow, oh in rooms:
            if rx < ox + ow + padding and rx + rw + padding > ox and \
               ry < oy + oh + padding and ry + rh + padding > oy:
                overlaps = True
                break
        if overlaps:
            continue

        rooms.append((rx, ry, rw, rh))
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                grid[y][x] = 0

    for i in range(len(rooms) - 1):
        _connect_rooms_2d(grid, rooms[i], rooms[i + 1], size)

    if level > 3:
        extra = min(3 + level // 4, 6)
        for _ in range(extra):
            a, b = random.sample(range(len(rooms)), 2)
            _connect_rooms_2d(grid, rooms[a], rooms[b], size)

    _place_traps(grid, rooms, level, size)
    _place_doors(grid, rooms, level, size)
    _place_secrets(grid, size)

    first_room = rooms[0]
    spawn_x = first_room[0] + first_room[2] // 2 + 0.5
    spawn_y = first_room[1] + first_room[3] // 2 + 0.5

    last_room = rooms[-1]
    exit_x = last_room[0] + last_room[2] // 2 + 0.5
    exit_y = last_room[1] + last_room[3] // 2 + 0.5
    grid[int(exit_y)][int(exit_x)] = C.WALL_EXIT

    enemy_spawns = []
    enemy_pool = ["drone", "drone", "guard"]
    if level >= 3:
        enemy_pool.append("guard")
    if level >= 5:
        enemy_pool.append("elite")
    if level >= 8:
        enemy_pool.append("elite")
        enemy_pool.append("elite")

    boss_room_idx = len(rooms) - 1
    for i, room in enumerate(rooms):
        if i == 0 or i == boss_room_idx:
            continue
        if random.random() < 0.7:
            ex = room[0] + random.randint(1, room[2] - 2) + 0.5
            ey = room[1] + random.randint(1, room[3] - 2) + 0.5
            etype = random.choice(enemy_pool)
            enemy_spawns.append((ex, ey, etype))

    boss_room = rooms[boss_room_idx]
    bx = boss_room[0] + boss_room[2] // 2 + 0.5
    by = boss_room[1] + boss_room[3] // 2 + 0.5
    enemy_spawns.append((bx, by, "boss"))

    _open_boss_path(grid, rooms, boss_room_idx, size)

    return WorldMap2D(grid, (spawn_x, spawn_y), (exit_x, exit_y), enemy_spawns)


def _connect_rooms_2d(grid, room1, room2, size):
    cx1 = room1[0] + room1[2] // 2
    cy1 = room1[1] + room1[3] // 2
    cx2 = room2[0] + room2[2] // 2
    cy2 = room2[1] + room2[3] // 2

    if random.random() < 0.5:
        _carve_h(grid, cx1, cx2, cy1, size)
        _carve_v(grid, cy1, cy2, cx2, size)
    else:
        _carve_v(grid, cy1, cy2, cx1, size)
        _carve_h(grid, cx1, cx2, cy2, size)


def _carve_h(grid, x1, x2, y, size):
    start, end = min(x1, x2), max(x1, x2)
    for x in range(start, end + 1):
        if 1 <= y < size - 1 and 1 <= x < size - 1:
            grid[y][x] = 0
            if y + 1 < size - 1:
                grid[y + 1][x] = 0


def _carve_v(grid, y1, y2, x, size):
    start, end = min(y1, y2), max(y1, y2)
    for y in range(start, end + 1):
        if 1 <= y < size - 1 and 1 <= x < size - 1:
            grid[y][x] = 0
            if x + 1 < size - 1:
                grid[y][x + 1] = 0


def _place_traps(grid, rooms, level, size):
    if level < 2:
        return
    num_traps = min(2 + level // 2, 10)
    for _ in range(num_traps * 10):
        rx = random.randint(1, size - 2)
        ry = random.randint(1, size - 2)
        if grid[ry][rx] == 0:
            neighbors = 0
            for ny, nx in [(ry-1, rx), (ry+1, rx), (ry, rx-1), (ry, rx+1)]:
                if 0 <= ny < size and 0 <= nx < size and grid[ny][nx] == 1:
                    neighbors += 1
            in_spawn_room = False
            for ox, oy, ow, oh in rooms[:1]:
                if ox <= rx < ox + ow and oy <= ry < oy + oh:
                    in_spawn_room = True
                    break
            in_exit_room = False
            for ox, oy, ow, oh in rooms[-1:]:
                if ox <= rx < ox + ow and oy <= ry < oy + oh:
                    in_exit_room = True
                    break
            if neighbors >= 2 and not in_spawn_room and not in_exit_room:
                grid[ry][rx] = C.WALL_TRAP
                break


def _place_doors(grid, rooms, level, size):
    num_doors = min(2 + level // 3, 6)
    for _ in range(num_doors * 20):
        rx = random.randint(1, size - 2)
        ry = random.randint(1, size - 2)
        if grid[ry][rx] == 0:
            neighbors = 0
            for ny, nx in [(ry-1, rx), (ry+1, rx), (ry, rx-1), (ry, rx+1)]:
                if 0 <= ny < size and 0 <= nx < size and grid[ny][nx] == 1:
                    neighbors += 1
            if neighbors >= 2:
                grid[ry][rx] = C.WALL_DOOR
                break


def _place_secrets(grid, size):
    for _ in range(3 * 50):
        sx = random.randint(1, size - 2)
        sy = random.randint(1, size - 2)
        if grid[sy][sx] == 1:
            empty_neighbors = 0
            for ny, nx in [(sy-1, sx), (sy+1, sx), (sy, sx-1), (sy, sx+1)]:
                if 0 <= ny < size and 0 <= nx < size and grid[ny][nx] == 0:
                    empty_neighbors += 1
            if empty_neighbors >= 1:
                grid[sy][sx] = C.WALL_SECRET
                break


def _open_boss_path(grid, rooms, boss_idx, size):
    boss_room = rooms[boss_idx]
    for y in range(boss_room[1], boss_room[1] + boss_room[3]):
        for x in range(boss_room[0], boss_room[0] + boss_room[2]):
            if 0 <= y < size and 0 <= x < size:
                if grid[y][x] in (C.WALL_DOOR, C.WALL_STONE, C.WALL_METAL):
                    grid[y][x] = 0
