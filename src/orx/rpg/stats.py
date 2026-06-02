"""Player stats: Speed, Logic-Core, Hacking-Potency."""

from __future__ import annotations

from orx import constants as C


class PlayerStats:
    """RPG stat tracking for the player."""

    def __init__(self):
        self.level = 1
        self.xp = 0
        self.xp_to_next = C.XP_BASE
        self.speed = C.STAT_SPEED_BASE
        self.logic = C.STAT_LOGIC_BASE
        self.hacking = C.STAT_HACKING_BASE
        self.stat_points = 0
        self.gold = 0
        self.inventory: list[dict] = []
        self.equipped: dict[str, str | None] = {
            "weapon": None,
            "armor": None,
            "accessory": None,
        }
        self.perm_attack_bonus = 0
        self.perm_defense_bonus = 0
        self.perm_speed_bonus = 0.0

    def add_xp(self, amount: int) -> bool:
        """Add XP. Returns True if leveled up."""
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next and self.level < C.MAX_LEVEL:
            self.xp -= self.xp_to_next
            self.level += 1
            self.stat_points += 3
            self.xp_to_next = int(C.XP_BASE * (C.XP_MULTIPLIER ** (self.level - 1)))
            leveled = True
        return leveled

    def allocate_point(self, stat: str) -> bool:
        if self.stat_points <= 0:
            return False
        if stat == "speed":
            self.speed += 0.1
        elif stat == "logic":
            self.logic += 0.1
        elif stat == "hacking":
            self.hacking += 0.1
        else:
            return False
        self.stat_points -= 1
        return True

    @property
    def speed_multiplier(self) -> float:
        return self.speed

    @property
    def damage_multiplier(self) -> float:
        return 1.0 + (self.logic - 1.0) * 0.5
