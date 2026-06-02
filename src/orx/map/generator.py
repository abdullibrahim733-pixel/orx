"""Procedural dungeon generation using BSP-like room placement."""

from __future__ import annotations

import random
from orx.map.world import WorldMap
from orx import constants as C


def generate_dungeon(seed: int | None = None) -> WorldMap:
    """Generate a procedural dungeon with rooms, corridors, doors, and secrets."""
    if seed is not None:
        random.seed(seed)
    else:
        seed = random.randint(0, 999999)

    w, h = C.MAP_WIDTH, C.MAP_HEIGHT
    grid = [[1] * w for _ in range(h)]

    rooms = []
    min_room = 4
    max_room = 8
    num_rooms = random.randint(6, 10)

    for _ in range(num_rooms * 10):
        rw = random.randint(min_room, max_room)
        rh = random.randint(min_room, max_room)
        rx = random.randint(1, w - rw - 1)
        ry = random.randint(1, h - rh - 1)

        overlaps = False
        for ox, oy, ow, oh in rooms:
            if rx < ox + ow + 1 and rx + rw + 1 > ox and ry < oy + oh + 1 and ry + rh + 1 > oy:
                overlaps = True
                break
        if overlaps:
            continue

        rooms.append((rx, ry, rw, rh))
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                grid[y][x] = 0

        if len(rooms) >= num_rooms:
            break

    for i in range(len(rooms) - 1):
        _connect_rooms(grid, rooms[i], rooms[i + 1])

    extra_connections = min(2, len(rooms) - 2)
    for _ in range(extra_connections):
        a, b = random.sample(range(len(rooms)), 2)
        _connect_rooms(grid, rooms[a], rooms[b])

    for _ in range(random.randint(2, 4)):
        for _ in range(100):
            dx = random.randint(1, w - 2)
            dy = random.randint(1, h - 2)
            if grid[dy][dx] == 0:
                neighbors = 0
                for ny, nx in [(dy-1, dx), (dy+1, dx), (dy, dx-1), (dy, dx+1)]:
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] != 0:
                        neighbors += 1
                if neighbors >= 2:
                    grid[dy][dx] = C.WALL_DOOR
                    break

    for _ in range(random.randint(1, 3)):
        for _ in range(100):
            sx = random.randint(1, w - 2)
            sy = random.randint(1, h - 2)
            if grid[sy][sx] != 0 and grid[sy][sx] != C.WALL_DOOR:
                empty_neighbors = 0
                for ny, nx in [(sy-1, sx), (sy+1, sx), (sy, sx-1), (sy, sx+1)]:
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == 0:
                        empty_neighbors += 1
                if empty_neighbors >= 1:
                    grid[sy][sx] = C.WALL_SECRET
                    break

    for _ in range(50):
        mx = random.randint(0, w - 1)
        my = random.randint(0, h - 1)
        if grid[my][mx] == 1:
            neighbors = 0
            for ny, nx in [(my-1, mx), (my+1, mx), (my, mx-1), (my, mx+1)]:
                if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == 0:
                    neighbors += 1
            if neighbors >= 2:
                grid[my][mx] = 0

    first_room = rooms[0]
    spawn_x = first_room[0] + first_room[2] // 2 + 0.5
    spawn_y = first_room[1] + first_room[3] // 2 + 0.5

    enemy_spawns = []
    enemy_type_pool = ["drone", "drone", "guard", "guard", "elite"]
    for room in rooms[1:]:
        ex = room[0] + random.randint(1, room[2] - 2) + 0.5
        ey = room[1] + random.randint(1, room[3] - 2) + 0.5
        etype = random.choice(enemy_type_pool)
        enemy_spawns.append((ex, ey, etype))

    if len(rooms) > 3:
        last = rooms[-1]
        bx = last[0] + last[2] // 2 + 0.5
        by = last[1] + last[3] // 2 + 0.5
        enemy_spawns.append((bx, by, "boss"))

    return WorldMap(grid, (spawn_x, spawn_y), enemy_spawns)


def _connect_rooms(grid: list[list[int]], room1: tuple, room2: tuple) -> None:
    cx1 = room1[0] + room1[2] // 2
    cy1 = room1[1] + room1[3] // 2
    cx2 = room2[0] + room2[2] // 2
    cy2 = room2[1] + room2[3] // 2

    x, y = cx1, cy1
    while x != cx2:
        if 0 < y < len(grid) and 0 <= x < len(grid[0]):
            grid[y][x] = 0
        x += 1 if cx2 > cx1 else -1
    while y != cy2:
        if 0 < y < len(grid) and 0 <= x < len(grid[0]):
            grid[y][x] = 0
        y += 1 if cy2 > cy1 else -1
