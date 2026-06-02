"""Multi-level management and level transitions."""

from __future__ import annotations

from orx.map.generator import generate_dungeon
from orx.map.world import WorldMap
from orx.entities.enemy import Enemy
from orx.world.boss import BossAI
from orx.world.npc import NPC
from orx.world.hierarchy import generate_boss_ladder
import random


class LevelManager:
    """Manages multiple levels with increasing difficulty."""

    def __init__(self):
        self.current_level = 1
        self.max_level = 10
        self.world: WorldMap | None = None
        self.enemies: list[Enemy | BossAI] = []
        self.npcs: list[NPC] = []
        self.boss_ladder = generate_boss_ladder(self.max_level)
        self.cleared = False
        self._generate_level(1)

    def _generate_level(self, level: int) -> None:
        self.current_level = level
        seed = 42 + level * 17
        self.world = generate_dungeon(seed=seed)

        self.enemies = []
        enemy_pool = ["drone", "drone", "guard"]
        if level >= 3:
            enemy_pool.append("elite")
        if level >= 5:
            enemy_pool.append("elite")
            enemy_pool.append("elite")

        for ex, ey, _ in self.world.enemy_spawns[:-1]:
            etype = random.choice(enemy_pool)
            enemy = Enemy(ex, ey, etype)
            enemy.health = int(enemy.health * (1.0 + level * 0.15))
            enemy.damage = int(enemy.damage * (1.0 + level * 0.1))
            enemy.xp = int(enemy.xp * (1.0 + level * 0.1))
            self.enemies.append(enemy)

        if len(self.world.enemy_spawns) > 0:
            boss_data = self.world.enemy_spawns[-1]
            boss_name = self.boss_ladder.get(level, "Royal Guard")
            boss = BossAI(boss_data[0], boss_data[1], boss_name)
            boss.max_health = int(boss.max_health * (1.0 + level * 0.25))
            boss.health = boss.max_health
            boss.damage = int(boss.damage * (1.0 + level * 0.15))
            boss.phase_threshold = boss.max_health / boss.max_phases
            self.enemies.append(boss)

        self.npcs = []
        if level > 1:
            npc_rooms = random.sample(self.world.enemy_spawns[:-1], min(1, len(self.world.enemy_spawns) - 1))
            if npc_rooms:
                npc_type = random.choice(["merchant", "scout", "hacker"])
                npc = NPC(npc_rooms[0][0], npc_rooms[0][1], npc_type)
                if self.world:
                    for _ in range(3):
                        nx = npc.x + random.uniform(-3, 3)
                        ny = npc.y + random.uniform(-3, 3)
                        if not self.world.is_wall(int(nx), int(ny)):
                            npc.add_patrol_point(nx, ny)
                self.npcs.append(npc)

        self.cleared = False

    def next_level(self) -> str:
        if self.current_level < self.max_level:
            boss_name = self.boss_ladder.get(self.current_level + 1, "Unknown")
            self._generate_level(self.current_level + 1)
            return f"LEVEL {self.current_level}: {boss_name}"
        return "FINAL LEVEL CLEARED"

    @property
    def all_enemies_dead(self) -> bool:
        return all(not e.is_alive for e in self.enemies)

    @property
    def boss_alive(self) -> bool:
        return any(isinstance(e, BossAI) and e.is_alive for e in self.enemies)
