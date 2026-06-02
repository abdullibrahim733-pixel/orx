"""Game constants for Orx."""

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 120

FOV = 60.0
HALF_FOV = FOV / 2.0
NUM_RAYS = 320
STRIP_WIDTH = SCREEN_WIDTH // NUM_RAYS
MAX_DEPTH = 20.0

TILE_SIZE = 1.0
MAP_WIDTH = 24
MAP_HEIGHT = 24

PLAYER_SPEED = 3.0
PLAYER_ROT_SPEED = 2.5
PLAYER_RADIUS = 0.25

WALL_STONE = 1
WALL_METAL = 2
WALL_DOOR = 3
WALL_SECRET = 4
WALL_TRAP = 5
WALL_EXIT = 6

ENEMY_TYPES = {
    "drone":  {"health": 30,  "damage": 5,  "speed": 1.5, "xp": 10,  "color": (220,  60,  40)},
    "guard":  {"health": 60,  "damage": 12, "speed": 1.0, "xp": 25,  "color": (180,  40, 180)},
    "elite":  {"health": 100, "damage": 20, "speed": 1.8, "xp": 50,  "color": (255, 140,   0)},
    "boss":   {"health": 300, "damage": 35, "speed": 0.8, "xp": 200, "color": (255,   0,   0)},
}

WEAPON_DAMAGE = 15
WEAPON_FIRE_RATE = 0.25
WEAPON_AMMO_MAX = 50
WEAPON_AMMO_START = 20

PLAYER_HEALTH_MAX = 100
PLAYER_HEALTH_START = 100
PLAYER_ARMOR_MAX = 200
PLAYER_ARMOR_START = 0

STAT_SPEED_BASE = 1.0
STAT_LOGIC_BASE = 1.0
STAT_HACKING_BASE = 1.0

XP_BASE = 50
XP_MULTIPLIER = 1.5
MAX_LEVEL = 50

# DOOM-style: deep blood-red sky fading to dark maroon
COLOR_SKY_TOP    = (60,  8,  8)
COLOR_SKY_BOTTOM = (30,  4,  4)

# DOOM-style: dark brownish-gray floor
COLOR_FLOOR_TOP    = (38, 30, 22)
COLOR_FLOOR_BOTTOM = (18, 12,  8)

MINIMAP_SIZE = 140
MINIMAP_TILE = 5

# DOOM HUD bar height (bottom strip)
HUD_BAR_HEIGHT = 80

# --- 2D mode constants ---
TILE_SIZE_2D = 28
VIEW_TILES_X = SCREEN_WIDTH // TILE_SIZE_2D + 2
VIEW_TILES_Y = SCREEN_HEIGHT // TILE_SIZE_2D + 2
PLAYER_RADIUS_2D = 10
PLAYER_SPEED_2D = 120.0
ENEMY_SPEED_2D = 60.0
BOSS_SPEED_2D = 45.0
PROJECTILE_SPEED_2D = 250.0
ATTACK_RANGE_2D = 120
ATTACK_COOLDOWN_2D = 0.3
MAX_LEVELS_2D = 25
TRAP_DAMAGE = 15
TRAP_COOLDOWN = 1.0

# --- Shop / Gold constants ---
GOLD_PER_KILL_BASE = 50
GOLD_BOSS_BONUS = 500
GOLD_PER_LEVEL_BONUS = 100
SHOP_TAB_CYCLE = ["game", "stats", "shop"]
ITEM_TIERS = {
    "E-Rank":   {"min_level": 1,  "color": (160, 120,  60)},
    "C-Rank":   {"min_level": 21, "color": (160, 160, 200)},
    "A-Rank":   {"min_level": 41, "color": (255, 200,  50)},
    "S-Rank":   {"min_level": 51, "color": (255,  50,  50)},
}
MAX_INVENTORY_SLOTS = 24
MAX_CONSUMABLE_STACK = 99
DAILY_DEAL_SLOTS = 3
