"""NPC behavioral AI with patrol, alert, and idle states."""

from __future__ import annotations

import math
import random
from orx.map.world import WorldMap


class NPC:
    """Non-player character with patrol routes and dialogue."""

    def __init__(self, x: float, y: float, npc_type: str = "merchant"):
        self.x = x
        self.y = y
        self.type = npc_type
        self.state = "idle"
        self.patrol_points: list[tuple[float, float]] = []
        self.current_patrol = 0
        self.speed = 1.0
        self.wait_timer = random.uniform(1.0, 3.0)
        self.dialogue = self._get_dialogue()
        self.interacted = False
        self.size = 0.3

    def _get_dialogue(self) -> list[str]:
        dialogues = {
            "merchant": [
                "Shadow energy detected nearby...",
                "I trade in code fragments. Come back when you've absorbed more.",
                "The Monarchy grows stronger. You must ascend.",
                "I've seen your path, Orx. The throne awaits.",
            ],
            "scout": [
                "Enemy patrol ahead. Watch your six.",
                "The boss in this sector uses projectile attacks.",
                "I found a secret wall. Check the eastern corridor.",
                "Your shadow absorption rate is above average.",
            ],
            "hacker": [
                "I've mapped the Cy-FX firewall. Hacking-Potency will help you breach it.",
                "Each level's boss has a weakness in phase 2.",
                "Speed is key — don't get cornered.",
                "Logic-Core boosts your weapon. Invest wisely.",
            ],
        }
        return dialogues.get(self.type, ["..."])

    def add_patrol_point(self, x: float, y: float) -> None:
        self.patrol_points.append((x, y))

    def update(self, dt: float, world: WorldMap, player_x: float, player_y: float) -> None:
        if self.state == "idle":
            self.wait_timer -= dt
            if self.wait_timer <= 0:
                if self.patrol_points:
                    self.state = "patrolling"
                    self.current_patrol = 0
                else:
                    self.wait_timer = random.uniform(2.0, 5.0)

        elif self.state == "patrolling":
            if self.current_patrol < len(self.patrol_points):
                target = self.patrol_points[self.current_patrol]
                dx = target[0] - self.x
                dy = target[1] - self.y
                dist = math.hypot(dx, dy)

                if dist < 0.3:
                    self.current_patrol += 1
                    if self.current_patrol >= len(self.patrol_points):
                        self.state = "idle"
                        self.wait_timer = random.uniform(1.0, 3.0)
                else:
                    nx, ny = dx / dist, dy / dist
                    new_x = self.x + nx * self.speed * dt
                    new_y = self.y + ny * self.speed * dt
                    if not world.is_wall(int(new_x), int(self.y)):
                        self.x = new_x
                    if not world.is_wall(int(self.x), int(new_y)):
                        self.y = new_y

        dist_to_player = math.hypot(self.x - player_x, self.y - player_y)
        if dist_to_player < 1.5:
            self.state = "alert"

    def interact(self) -> str | None:
        if self.dialogue:
            line = random.choice(self.dialogue)
            return line
        return None

    def get_screen_info(self, player_x: float, player_y: float, player_angle: float) -> dict | None:
        dx = self.x - player_x
        dy = self.y - player_y
        dist = math.hypot(dx, dy)

        if dist > 15.0:
            return None

        npc_angle = math.atan2(dy, dx)
        rel_angle = npc_angle - player_angle
        while rel_angle > math.pi:
            rel_angle -= 2 * math.pi
        while rel_angle < -math.pi:
            rel_angle += 2 * math.pi

        half_fov = math.radians(30)
        if abs(rel_angle) > half_fov + 0.2:
            return None

        screen_x = int((0.5 + rel_angle / (2 * half_fov)) * 960)
        sprite_height = int(540 / dist * self.size * 2)
        sprite_width = int(sprite_height * 0.6)
        shade = max(0.15, min(1.0, 1.0 - (dist / 15.0)))

        return {
            "screen_x": screen_x,
            "height": sprite_height,
            "width": sprite_width,
            "distance": dist,
            "shade": shade,
        }
