"""Enemy AI with chase, attack, and death states."""

from __future__ import annotations

import math
from orx.map.world import WorldMap
from orx import constants as C


class Enemy:
    """Enemy entity with AI behavior."""

    def __init__(self, x: float, y: float, enemy_type: str):
        self.x = x
        self.y = y
        self.type = enemy_type
        stats = C.ENEMY_TYPES.get(enemy_type, C.ENEMY_TYPES["drone"])
        self.max_health = stats["health"]
        self.health = self.max_health
        self.damage = stats["damage"]
        self.speed = stats["speed"]
        self.xp = stats["xp"]
        self.color = stats["color"]
        self.state = "idle"
        self.attack_cooldown = 0.0
        self.alert_range = 8.0 if enemy_type != "boss" else 12.0
        self.attack_range = 0.8 if enemy_type != "boss" else 1.5
        self.death_timer = 0.0
        self.size = 0.4 if enemy_type != "boss" else 0.6

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    @property
    def is_dead(self) -> bool:
        return self.health <= 0 and self.death_timer <= 0

    def update(self, dt: float, player_x: float, player_y: float,
               player_angle: float, world: WorldMap) -> None:
        if self.health <= 0:
            self.death_timer -= dt
            return

        dist = math.hypot(self.x - player_x, self.y - player_y)

        if dist <= self.alert_range:
            if world.line_of_sight(self.x, self.y, player_x, player_y):
                self.state = "chase"
            else:
                self.state = "idle"
        else:
            self.state = "idle"

        if self.state == "chase":
            if dist > self.attack_range:
                dx = player_x - self.x
                dy = player_y - self.y
                length = max(0.01, math.hypot(dx, dy))
                nx, ny = dx / length, dy / length

                new_x = self.x + nx * self.speed * dt
                new_y = self.y + ny * self.speed * dt

                if not world.is_wall(int(new_x), int(self.y)):
                    self.x = new_x
                if not world.is_wall(int(self.x), int(new_y)):
                    self.y = new_y
            else:
                self.attack_cooldown -= dt
                if self.attack_cooldown <= 0:
                    self.attack_cooldown = 1.0
                    return self.damage
        return 0

    def take_damage(self, amount: float) -> None:
        self.health = max(0, self.health - amount)
        if self.health <= 0:
            self.death_timer = 1.0
            self.state = "dead"

    def get_screen_info(self, player_x: float, player_y: float, player_angle: float) -> dict | None:
        if self.is_dead:
            return None

        dx = self.x - player_x
        dy = self.y - player_y
        dist = math.hypot(dx, dy)

        if dist > C.MAX_DEPTH or dist < 0.3:
            return None

        enemy_angle = math.atan2(dy, dx)
        rel_angle = enemy_angle - player_angle

        while rel_angle > math.pi:
            rel_angle -= 2 * math.pi
        while rel_angle < -math.pi:
            rel_angle += 2 * math.pi

        half_fov = math.radians(C.HALF_FOV)
        if abs(rel_angle) > half_fov + 0.2:
            return None

        screen_x = int((0.5 + rel_angle / (2 * half_fov)) * C.SCREEN_WIDTH)
        sprite_height = int(C.SCREEN_HEIGHT / dist * self.size * 2)
        sprite_width = int(sprite_height * 0.6)

        shade = max(0.15, min(1.0, 1.0 - (dist / C.MAX_DEPTH)))

        return {
            "screen_x": screen_x,
            "height": sprite_height,
            "width": sprite_width,
            "distance": dist,
            "shade": shade,
        }
