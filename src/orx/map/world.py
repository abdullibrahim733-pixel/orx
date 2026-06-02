"""World map data and accessors."""

from __future__ import annotations

import math


class WorldMap:
    """2D grid-based map with wall types, doors, and spawn points."""

    def __init__(self, grid: list[list[int]], spawn: tuple[float, float],
                 enemy_spawns: list[tuple[float, float, str]] | None = None):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height else 0
        self.spawn = spawn
        self.enemy_spawns = enemy_spawns or []

    def is_wall(self, x: int, y: int) -> bool:
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return True
        return self.grid[y][x] != 0

    def get_tile(self, x: int, y: int) -> int:
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return 1
        return self.grid[y][x]

    def set_tile(self, x: int, y: int, value: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = value

    def line_of_sight(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        cx, cy = x1, y1

        steps = max(int(max(dx, dy) * 10), 1)
        for _ in range(steps):
            ix, iy = int(cx), int(cy)
            if self.is_wall(ix, iy):
                hit_x, hit_y = ix + 0.5, iy + 0.5
                dist_to_wall = math.hypot(hit_x - x1, hit_y - y1)
                dist_to_target = math.hypot(x2 - x1, y2 - y1)
                return dist_to_wall > dist_to_target
            cx += (x2 - x1) / steps
            cy += (y2 - y1) / steps
        return True
