"""The System Store — item database, transaction validation, daily rotation."""

from __future__ import annotations

import random
from orx import constants as C

ITEM_DB = {
    # ── E-Rank / Bronze (Lv. 1–20) ──
    "bronze_dagger": {
        "item_id": "bronze_dagger",
        "name": "Bronze Dagger",
        "tier": "E-Rank",
        "category": "weapon",
        "purchase_cost": 500,
        "sell_value": 100,
        "required_level": 1,
        "stock_limit": 1,
        "modifiers": {"attack_power": 5},
    },
    "cloth_bandage": {
        "item_id": "cloth_bandage",
        "name": "Cloth Bandage",
        "tier": "E-Rank",
        "category": "consumable",
        "purchase_cost": 150,
        "sell_value": 30,
        "required_level": 1,
        "stock_limit": 10,
        "modifiers": {"heal": 25},
    },
    "leather_armor": {
        "item_id": "leather_armor",
        "name": "Leather Armor",
        "tier": "E-Rank",
        "category": "armor",
        "purchase_cost": 800,
        "sell_value": 160,
        "required_level": 5,
        "stock_limit": 1,
        "modifiers": {"defense": 3},
    },
    "steel_dagger": {
        "item_id": "steel_dagger",
        "name": "Steel Dagger",
        "tier": "E-Rank",
        "category": "weapon",
        "purchase_cost": 1200,
        "sell_value": 240,
        "required_level": 10,
        "stock_limit": 1,
        "modifiers": {"attack_power": 10},
    },
    "light_helm": {
        "item_id": "light_helm",
        "name": "Light Helm",
        "tier": "E-Rank",
        "category": "accessory",
        "purchase_cost": 600,
        "sell_value": 120,
        "required_level": 8,
        "stock_limit": 1,
        "modifiers": {"defense": 2},
    },
    # ── C-Rank / Silver (Lv. 21–50) ──
    "mana_dagger": {
        "item_id": "mana_dagger",
        "name": "Mana-Infused Blade",
        "tier": "C-Rank",
        "category": "weapon",
        "purchase_cost": 5000,
        "sell_value": 1000,
        "required_level": 21,
        "stock_limit": 1,
        "modifiers": {"attack_power": 25, "mana_leech": 0.05},
    },
    "elixir_cure": {
        "item_id": "elixir_cure",
        "name": "Status-Cure Elixir",
        "tier": "C-Rank",
        "category": "consumable",
        "purchase_cost": 2000,
        "sell_value": 400,
        "required_level": 21,
        "stock_limit": 5,
        "modifiers": {"cure_status": True},
    },
    "weight_training": {
        "item_id": "weight_training",
        "name": "Weight Training Kit",
        "tier": "C-Rank",
        "category": "permanent",
        "purchase_cost": 8000,
        "sell_value": 0,
        "required_level": 25,
        "stock_limit": 1,
        "modifiers": {"perm_attack": 5, "perm_defense": 2},
    },
    "silver_plate": {
        "item_id": "silver_plate",
        "name": "Silver Plate Armor",
        "tier": "C-Rank",
        "category": "armor",
        "purchase_cost": 6000,
        "sell_value": 1200,
        "required_level": 25,
        "stock_limit": 1,
        "modifiers": {"defense": 10},
    },
    # ── A-Rank / Gold (Lv. 41+) ──
    "mythic_dagger": {
        "item_id": "mythic_dagger",
        "name": "Mythic Void Dagger",
        "tier": "A-Rank",
        "category": "weapon",
        "purchase_cost": 25000,
        "sell_value": 5000,
        "required_level": 41,
        "stock_limit": 1,
        "modifiers": {"attack_power": 60, "crit_chance": 0.1},
    },
    "absolute_potion": {
        "item_id": "absolute_potion",
        "name": "Absolute Recovery Potion",
        "tier": "A-Rank",
        "category": "consumable",
        "purchase_cost": 15000,
        "sell_value": 3000,
        "required_level": 41,
        "stock_limit": 3,
        "modifiers": {"heal": 999},
    },
    # ── S-Rank / Obsidian (Lv. 51+) ──
    "shadow_dagger": {
        "item_id": "shadow_dagger",
        "name": "Shadow Monarch's Fang",
        "tier": "S-Rank",
        "category": "weapon",
        "purchase_cost": 100000,
        "sell_value": 20000,
        "required_level": 51,
        "stock_limit": 1,
        "modifiers": {"attack_power": 150, "shadow_damage": 0.3},
    },
    "skill_scroll_haste": {
        "item_id": "skill_scroll_haste",
        "name": "Skill Scroll: Haste",
        "tier": "S-Rank",
        "category": "permanent",
        "purchase_cost": 75000,
        "sell_value": 0,
        "required_level": 51,
        "stock_limit": 1,
        "modifiers": {"perm_speed": 0.2},
    },
}

ALL_ITEM_IDS = list(ITEM_DB.keys())


class ShopManager:
    """Manages shop inventory, daily deals, and purchase validation."""

    def __init__(self, player_level: int = 1):
        self.player_level = player_level
        self.inventory: dict[str, int] = {}
        for item_id in ALL_ITEM_IDS:
            self.inventory[item_id] = ITEM_DB[item_id]["stock_limit"]

        self.daily_deal_ids: list[str] = []
        self.daily_deals_refreshed = 0
        self._refresh_daily_deals()

    def _refresh_daily_deals(self) -> None:
        pool = [iid for iid in ALL_ITEM_IDS
                if ITEM_DB[iid]["required_level"] <= self.player_level + 10]
        if len(pool) >= C.DAILY_DEAL_SLOTS:
            self.daily_deal_ids = random.sample(pool, C.DAILY_DEAL_SLOTS)
        else:
            self.daily_deal_ids = list(pool)
        self.daily_deals_refreshed += 1

    def refresh_if_needed(self, dungeons_cleared: int) -> None:
        if dungeons_cleared > self.daily_deals_refreshed * 3:
            self._refresh_daily_deals()

    def get_visible_items(self, player_level: int) -> list[dict]:
        """Return items the player's level can see (tier-unlocked)."""
        visible = []
        for item_id in ALL_ITEM_IDS:
            item = ITEM_DB[item_id]
            if player_level >= item["required_level"]:
                entry = dict(item)
                entry["available_stock"] = self.inventory.get(item_id, 0)
                entry["is_daily_deal"] = item_id in self.daily_deal_ids
                visible.append(entry)
        return visible

    def can_purchase(self, item_id: str, player_gold: int,
                     player_level: int, inventory_count: int) -> tuple[bool, str]:
        item = ITEM_DB.get(item_id)
        if item is None:
            return False, "Item not found."

        if self.inventory.get(item_id, 0) <= 0:
            return False, "Out of stock."

        if player_level < item["required_level"]:
            return (False,
                    f"Your level is insufficient. (Req: {item['required_level']})")

        if player_gold < item["purchase_cost"]:
            return (False,
                    f"Not enough Gold. (Cost: {item['purchase_cost']})")

        if inventory_count >= C.MAX_INVENTORY_SLOTS:
            return False, "Inventory full."

        return True, "OK"

    def execute_purchase(self, item_id: str) -> dict | None:
        stock = self.inventory.get(item_id, 0)
        if stock <= 0:
            return None
        self.inventory[item_id] = stock - 1
        item = ITEM_DB[item_id]
        return dict(item)
