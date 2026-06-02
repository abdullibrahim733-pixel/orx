"""Simple particle system for effects."""

from __future__ import annotations

import math
import random
import pygame


class Particle:
    """Single particle with position, velocity, lifetime."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 life: float, color: tuple[int, int, int], size: int = 2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size


class ParticleSystem:
    """Manages particles for muzzle flash, blood, explosions."""

    def __init__(self):
        self.particles: list[Particle] = []

    def emit_muzzle_flash(self, screen_x: int, screen_y: int) -> None:
        for _ in range(15):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 200)
            self.particles.append(Particle(
                screen_x, screen_y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                random.uniform(0.1, 0.3),
                random.choice([(255, 255, 100), (255, 200, 50), (255, 100, 0)]),
                random.randint(2, 4)
            ))

    def emit_blood(self, screen_x: int, screen_y: int) -> None:
        for _ in range(10):
            angle = random.uniform(-math.pi / 2, math.pi / 2)
            speed = random.uniform(30, 120)
            self.particles.append(Particle(
                screen_x, screen_y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 50,
                random.uniform(0.3, 0.6),
                random.choice([(180, 0, 0), (140, 0, 0), (100, 0, 0)]),
                random.randint(1, 3)
            ))

    def update(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += 200 * dt
                alive.append(p)
        self.particles = alive

    def render(self, screen: pygame.Surface) -> None:
        for p in self.particles:
            alpha = min(255, int((p.life / p.max_life) * 255))
            color_with_alpha = (*p.color, alpha)
            s = pygame.Surface((p.size, p.size), pygame.SRCALPHA)
            pygame.draw.circle(s, color_with_alpha, (p.size // 2, p.size // 2), p.size // 2)
            screen.blit(s, (int(p.x - p.size / 2), int(p.y - p.size / 2)))
