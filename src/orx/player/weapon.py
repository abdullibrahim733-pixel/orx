"""Weapon system with shooting and ammo management."""

from __future__ import annotations

import math
from orx import constants as C
from orx.entities.enemy import Enemy


class Weapon:
    """First-person weapon with ammo and fire rate."""

    def __init__(self):
        self.ammo = C.WEAPON_AMMO_START
        self.damage = C.WEAPON_DAMAGE
        self.fire_rate = C.WEAPON_FIRE_RATE
        self.cooldown = 0.0
        self.firing = False
        self.shoot_anim = 0.0
        self.muzzle_flash = False
        self.hits: list[Enemy] = []

    def shoot(self, player_x: float, player_y: float, player_angle: float,
              enemies: list[Enemy]) -> list[Enemy]:
        if self.cooldown > 0 or self.ammo <= 0:
            return []

        self.cooldown = self.fire_rate
        self.ammo -= 1
        self.shoot_anim = 0.15
        self.muzzle_flash = True

        best_enemy = None
        best_dist = C.MAX_DEPTH

        for enemy in enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.x - player_x
            dy = enemy.y - player_y
            dist = math.hypot(dx, dy)

            if dist > C.MAX_DEPTH:
                continue

            enemy_angle = math.atan2(dy, dx)
            angle_diff = abs(_normalize_angle(enemy_angle - player_angle))

            hit_threshold = math.atan2(0.3, dist)
            if angle_diff < hit_threshold and dist < best_dist:
                best_dist = dist
                best_enemy = enemy

        if best_enemy is not None:
            best_enemy.take_damage(self.damage)
            return [best_enemy]
        return []

    def update(self, dt: float) -> None:
        if self.cooldown > 0:
            self.cooldown -= dt
        if self.shoot_anim > 0:
            self.shoot_anim -= dt
            if self.shoot_anim <= 0:
                self.muzzle_flash = False

    def reload(self, amount: int) -> None:
        self.ammo = min(self.ammo + amount, C.WEAPON_AMMO_MAX)

    @property
    def is_ready(self) -> bool:
        return self.cooldown <= 0 and self.ammo > 0


def _normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle
