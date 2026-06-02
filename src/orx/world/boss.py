"""Boss AI with multi-phase attacks and behavioral patterns."""

from __future__ import annotations

import math
import random
from orx.entities.enemy import Enemy
from orx.map.world import WorldMap


class BossAI(Enemy):
    """Boss enemy with phases, special attacks, and patterns."""

    def __init__(self, x: float, y: float, boss_name: str = "Royal Guard"):
        super().__init__(x, y, "boss")
        self.name = boss_name
        self.phase = 1
        self.max_phases = 3
        self.phase_threshold = self.max_health / self.max_phases
        self.attack_pattern = 0
        self.pattern_timer = 0.0
        self.special_cooldown = 3.0
        self.ranged_attack_range = 5.0
        self.projectiles: list[dict] = []
        self.enraged = False
        self.strafe_angle = random.uniform(0, 2 * math.pi)
        self.strafe_timer = 0.0

    def update(self, dt: float, player_x: float, player_y: float,
               player_angle: float, world: WorldMap) -> int:
        if self.health <= 0:
            self.death_timer -= dt
            return 0

        new_phase = min(self.max_phases, int((self.max_health - self.health) / self.phase_threshold) + 1)
        if new_phase > self.phase:
            self.phase = new_phase
            self.enraged = self.phase >= 2

        speed_mult = 1.0 + (self.phase - 1) * 0.3
        damage_mult = 1.0 + (self.phase - 1) * 0.5

        self.pattern_timer -= dt
        if self.pattern_timer <= 0:
            self.attack_pattern = (self.attack_pattern + 1) % 3
            self.pattern_timer = random.uniform(3.0, 6.0)

        self.strafe_timer -= dt
        if self.strafe_timer <= 0:
            self.strafe_angle = random.uniform(0, 2 * math.pi)
            self.strafe_timer = random.uniform(1.0, 3.0)

        damage_dealt = 0

        if self.attack_pattern == 0:
            damage_dealt = self._chase_and_attack(dt, player_x, player_y, world, speed_mult, damage_mult)
        elif self.attack_pattern == 1:
            damage_dealt = self._ranged_attack(dt, player_x, player_y, world, speed_mult, damage_mult)
        else:
            damage_dealt = self._strafe_attack(dt, player_x, player_y, world, speed_mult, damage_mult)

        self.special_cooldown -= dt
        if self.special_cooldown <= 0 and self.phase >= 2:
            self._special_attack(player_x, player_y, damage_mult)
            self.special_cooldown = max(5.0, 10.0 - self.phase * 2)

        for proj in self.projectiles[:]:
            proj["life"] -= dt
            proj["x"] += proj["vx"] * dt
            proj["y"] += proj["vy"] * dt

            p_dist = math.hypot(proj["x"] - player_x, proj["y"] - player_y)
            if p_dist < 0.5:
                damage_dealt += int(self.damage * damage_mult * 0.5)
                proj["life"] = 0

            if world.is_wall(int(proj["x"]), int(proj["y"])):
                proj["life"] = 0

        self.projectiles = [p for p in self.projectiles if p["life"] > 0]

        return damage_dealt

    def _chase_and_attack(self, dt: float, px: float, py: float,
                          world: WorldMap, speed_mult: float, damage_mult: float) -> int:
        dist = math.hypot(self.x - px, self.y - py)
        if dist > self.attack_range:
            dx = px - self.x
            dy = py - self.y
            length = max(0.01, math.hypot(dx, dy))
            nx, ny = dx / length, dy / length
            new_x = self.x + nx * self.speed * speed_mult * dt
            new_y = self.y + ny * self.speed * speed_mult * dt
            if not world.is_wall(int(new_x), int(self.y)):
                self.x = new_x
            if not world.is_wall(int(self.x), int(new_y)):
                self.y = new_y
        else:
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 0.8 / speed_mult
                return int(self.damage * damage_mult)
        return 0

    def _ranged_attack(self, dt: float, px: float, py: float,
                       world: WorldMap, speed_mult: float, damage_mult: float) -> int:
        dist = math.hypot(self.x - px, self.y - py)
        if dist > self.ranged_attack_range:
            dx = px - self.x
            dy = py - self.y
            length = max(0.01, math.hypot(dx, dy))
            self.x += (dx / length) * self.speed * speed_mult * 0.5 * dt
            self.y += (dy / length) * self.speed * speed_mult * 0.5 * dt
        else:
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 1.5 / speed_mult
                angle = math.atan2(py - self.y, px - self.x)
                speed = 4.0
                self.projectiles.append({
                    "x": self.x, "y": self.y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": 3.0,
                })
        return 0

    def _strafe_attack(self, dt: float, px: float, py: float,
                       world: WorldMap, speed_mult: float, damage_mult: float) -> int:
        strafe_dx = math.cos(self.strafe_angle) * self.speed * speed_mult * dt
        strafe_dy = math.sin(self.strafe_angle) * self.speed * speed_mult * dt
        if not world.is_wall(int(self.x + strafe_dx), int(self.y)):
            self.x += strafe_dx
        if not world.is_wall(int(self.x), int(self.y + strafe_dy)):
            self.y += strafe_dy

        dist = math.hypot(self.x - px, self.y - py)
        if dist < self.ranged_attack_range:
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 1.0
                for i in range(self.phase):
                    spread = (i - (self.phase - 1) / 2) * 0.3
                    angle = math.atan2(py - self.y, px - self.x) + spread
                    self.projectiles.append({
                        "x": self.x, "y": self.y,
                        "vx": math.cos(angle) * 3.0,
                        "vy": math.sin(angle) * 3.0,
                        "life": 2.0,
                    })
        return 0

    def _special_attack(self, px: float, py: float, damage_mult: float) -> None:
        for i in range(8):
            angle = (i / 8) * 2 * math.pi
            self.projectiles.append({
                "x": self.x, "y": self.y,
                "vx": math.cos(angle) * 2.5,
                "vy": math.sin(angle) * 2.5,
                "life": 4.0,
            })
