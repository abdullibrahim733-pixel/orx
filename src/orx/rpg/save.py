"""JSON save/load for player state."""

from __future__ import annotations

import json
import os
from orx import constants as C
from orx.rpg.stats import PlayerStats


SAVE_PATH = ".orx_save.json"


def save_game(stats: PlayerStats, level: int = 1) -> None:
    existing = {}
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    data = {
        "level": stats.level,
        "xp": stats.xp,
        "xp_to_next": stats.xp_to_next,
        "speed": stats.speed,
        "logic": stats.logic,
        "hacking": stats.hacking,
        "stat_points": stats.stat_points,
        "map_level": level,
        "gold": stats.gold,
        "inventory": stats.inventory,
        "equipped": stats.equipped,
        "perm_attack_bonus": stats.perm_attack_bonus,
        "perm_defense_bonus": stats.perm_defense_bonus,
        "perm_speed_bonus": stats.perm_speed_bonus,
    }
    for k, v in existing.items():
        if k.endswith("_2d"):
            data[k] = v
    if os.path.dirname(SAVE_PATH):
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
    with open(SAVE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_game() -> dict | None:
    if not os.path.exists(SAVE_PATH):
        return None
    try:
        with open(SAVE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def apply_save(stats: PlayerStats, data: dict) -> None:
    stats.level = data.get("level", 1)
    stats.xp = data.get("xp", 0)
    stats.xp_to_next = data.get("xp_to_next", C.XP_BASE)
    stats.speed = data.get("speed", C.STAT_SPEED_BASE)
    stats.logic = data.get("logic", C.STAT_LOGIC_BASE)
    stats.hacking = data.get("hacking", C.STAT_HACKING_BASE)
    stats.stat_points = data.get("stat_points", 0)
    stats.gold = data.get("gold", 0)
    stats.inventory = list(data.get("inventory", []))
    stats.equipped = dict(data.get("equipped", {
        "weapon": None, "armor": None, "accessory": None,
    }))
    stats.perm_attack_bonus = data.get("perm_attack_bonus", 0)
    stats.perm_defense_bonus = data.get("perm_defense_bonus", 0)
    stats.perm_speed_bonus = data.get("perm_speed_bonus", 0.0)
