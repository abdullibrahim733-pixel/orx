"""DDA ray-casting algorithm."""

from __future__ import annotations

import math
from orx.map.world import WorldMap
from orx import constants as C


class RayHit:
    """Result of a ray cast."""
    __slots__ = ("distance", "wall_type", "side", "tex_x", "hit_x", "hit_y")

    def __init__(self, distance: float, wall_type: int, side: int, tex_x: float, hit_x: float, hit_y: float):
        self.distance = distance
        self.wall_type = wall_type
        self.side = side
        self.tex_x = tex_x
        self.hit_x = hit_x
        self.hit_y = hit_y


def cast_rays(player_x: float, player_y: float, player_angle: float,
              world: WorldMap) -> list[RayHit]:
    """Cast NUM_RAYS rays and return hits."""
    hits = []
    fov_rad = math.radians(C.FOV)
    half_fov = fov_rad / 2.0
    angle_step = fov_rad / C.NUM_RAYS

    for i in range(C.NUM_RAYS):
        ray_angle = player_angle - half_fov + i * angle_step
        hit = _cast_single_ray(player_x, player_y, ray_angle, world)
        hits.append(hit)

    return hits


def _cast_single_ray(px: float, py: float, angle: float, world: WorldMap) -> RayHit:
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    dx = cos_a
    dy = sin_a

    map_x = int(px)
    map_y = int(py)

    if dx == 0:
        delta_dist_x = 1e30
        step_x = 0
    elif dx > 0:
        delta_dist_x = 1.0 / dx
        step_x = 1
    else:
        delta_dist_x = -1.0 / dx
        step_x = -1

    if dy == 0:
        delta_dist_y = 1e30
        step_y = 0
    elif dy > 0:
        delta_dist_y = 1.0 / dy
        step_y = 1
    else:
        delta_dist_y = -1.0 / dy
        step_y = -1

    if dx > 0:
        side_dist_x = (map_x + 1 - px) * delta_dist_x
    else:
        side_dist_x = (px - map_x) * delta_dist_x

    if dy > 0:
        side_dist_y = (map_y + 1 - py) * delta_dist_y
    else:
        side_dist_y = (py - map_y) * delta_dist_y

    side = 0
    max_steps = int(C.MAX_DEPTH * 2)

    for _ in range(max_steps):
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1

        if world.is_wall(map_x, map_y):
            if side == 0:
                perp_dist = (map_x - px + (1 - step_x) / 2) / dx if dx != 0 else C.MAX_DEPTH
                hit_x = py + perp_dist * dy
                tex_x = hit_x - int(hit_x)
            else:
                perp_dist = (map_y - py + (1 - step_y) / 2) / dy if dy != 0 else C.MAX_DEPTH
                hit_x = px + perp_dist * dx
                tex_x = hit_x - int(hit_x)

            tex_x = tex_x % 1.0
            wall_type = world.get_tile(map_x, map_y)
            return RayHit(perp_dist, wall_type, side, tex_x, map_x + 0.5, map_y + 0.5)

    return RayHit(C.MAX_DEPTH, 0, 0, 0.0, 0.0, 0.0)
