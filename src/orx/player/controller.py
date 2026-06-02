"""Player controller with WASD movement and mouse look."""

from __future__ import annotations

import math
import pygame
from orx.map.world import WorldMap
from orx import constants as C


class Player:
    """Player entity with position, rotation, and movement."""

    def __init__(self, x: float, y: float, angle: float = 0.0):
        self.x = x
        self.y = y
        self.angle = angle
        self.health = C.PLAYER_HEALTH_START
        self.speed_multiplier = 1.0
        self._move_x = 0.0
        self._move_y = 0.0
        self._rotating = 0.0

    @property
    def speed(self) -> float:
        return C.PLAYER_SPEED * self.speed_multiplier

    @property
    def rot_speed(self) -> float:
        return C.PLAYER_ROT_SPEED

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self._move_y = -1
            elif event.key == pygame.K_s:
                self._move_y = 1
            elif event.key == pygame.K_a:
                self._move_x = -1
            elif event.key == pygame.K_d:
                self._move_x = 1
            elif event.key == pygame.K_q:
                self._rotating = -1
            elif event.key == pygame.K_e:
                self._rotating = 1
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_w, pygame.K_s):
                self._move_y = 0
            elif event.key in (pygame.K_a, pygame.K_d):
                self._move_x = 0
            elif event.key in (pygame.K_q, pygame.K_e):
                self._rotating = 0
        elif event.type == pygame.MOUSEMOTION:
            rel = event.rel[0]
            self.angle += math.radians(rel * 0.15)

    def update(self, dt: float, world: WorldMap) -> None:
        self.angle += self._rotating * self.rot_speed * dt

        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        dx = (self._move_y * cos_a + self._move_x * sin_a) * self.speed * dt
        dy = (self._move_y * sin_a - self._move_x * cos_a) * self.speed * dt

        r = C.PLAYER_RADIUS
        new_x = self.x + dx
        if not world.is_wall(int(new_x + r), int(self.y + r)) and \
           not world.is_wall(int(new_x - r), int(self.y + r)) and \
           not world.is_wall(int(new_x + r), int(self.y - r)) and \
           not world.is_wall(int(new_x - r), int(self.y - r)):
            self.x = new_x

        new_y = self.y + dy
        if not world.is_wall(int(self.x + r), int(new_y + r)) and \
           not world.is_wall(int(self.x - r), int(new_y + r)) and \
           not world.is_wall(int(self.x + r), int(new_y - r)) and \
           not world.is_wall(int(self.x - r), int(new_y - r)):
            self.y = new_y

    def take_damage(self, amount: float) -> None:
        self.health = max(0, self.health - amount)
