# Orx: The Ascension of the Prime Cy-Orx

> *"In a world of rigid code, be the virus that rewrites the throne."*

**Orx** is a dual-mode retro-shooter / top-down dungeon crawler that blends 1990s FPS combat with Solo Leveling RPG progression. Choose your experience at launch: the classic **3D raycasted FPS** or the **2D top-down dungeon crawler** with emoji characters, 25 floors of procedurally generated traps, and competitive stat tracking.

Set in the year **3099**, you are a rogue entity navigating an intergalactic monarchy on a quest to claim the throne as the **Prime Cy-Orx**.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [2D Mode — Level Devil Dungeon Crawler](#2d-mode--level-devil-dungeon-crawler)
- [Controls](#controls)
- [Installation](#installation)
- [Usage](#usage)
- [Development Journal — Struggles & Fixes](#development-journal--struggles--fixes)
- [Narrative](#narrative)

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Runtime** | Python | >=3.12 (3.14) | Game loop, AI, state management, rendering orchestration |
| **Native extension** | C++ | C++17 | Performance-critical ray-casting and collision detection |
| **Game framework** | pygame-ce (Community Edition) | >=2.5.0 (2.5.7) | Display, input, audio, surface manipulation, blitting |
| **C++ bindings** | pybind11 | >=2.12 (3.0.4) | Bridge between Python and C++ extension modules |
| **Build system (Python)** | setuptools | >=69 | Package installation, C++ Extension build |
| **Build system (C++)** | CMake | >=3.15 | Alternative C++ extension build via `find_package(pybind11)` |
| **Linter / formatter** | ruff (dev) | >=0.6.0 (0.15.12) | Python code quality |
| **Low-level multimedia** | SDL2 | 2.32.10 | Windowing, input, audio mixing (via pygame-ce) |
| **SDL2 image** | SDL2_image | — | Image format loading (via pygame-ce) |
| **SDL2 mixer** | SDL2_mixer | — | Audio mixing (via pygame-ce) |
| **SDL2 ttf** | SDL2_ttf | — | Font rendering (via pygame-ce) |
| **Package manager** | pip | 26.1.1 | Dependency management |
| **Save system** | JSON | stdlib | Persist player progress to `.orx_save.json` |
| **Emoji rendering** | Noto Color Emoji | system | Color emoji glyphs for 2D mode characters |
| **OS target** | Arch Linux | — | Primary development and runtime platform |

---

## Architecture Overview

Orx now supports **two distinct game modes**, sharing the same RPG stat system, save/load, audio, and procedural asset generation:

```
┌──────────────────────────────────────────────────────────────────┐
│                        Launcher (game.py)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Start Screen                             │   │
│  │         [1] 3D — Classic Raycaster                       │   │
│  │         [2] 2D — Level Devil Mode                        │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │ choice                                │
│              ┌──────────┴──────────┐                            │
│              ▼                     ▼                             │
│  ┌───────────────────┐  ┌────────────────────┐                  │
│  │    Game3D         │  │    Game2D          │                  │
│  │  (game.py)        │  │  (game2d.py)       │                  │
│  │                   │  │                    │                  │
│  │  • DDA raycaster  │  │  • Top-down view   │                  │
│  │  • DOOM-style HUD │  │  • Emoji sprites   │                  │
│  │  • 10 levels      │  │  • 25 floors       │                  │
│  │  • CRT effects    │  │  • Traps & secrets  │                  │
│  │  • Weapon sprite  │  │  • Boss upgrades    │                  │
│  └────────┬──────────┘  └────────┬───────────┘                  │
│           │                      │                              │
│           └──────────┬───────────┘                              │
│                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Shared Systems                                 │   │
│  │  rpg/stats.py  rpg/save.py  audio/music.py               │   │
│  │  assets/procedural.py  world/hierarchy.py                │   │
│  │  entities/enemy.py  world/boss.py                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **Mode selection at the start screen** avoids cluttering the CLI with mode flags. The user presses `[1]` or `[2]` immediately on launch.
- **Shared RPG stats** across both modes means leveling up in one mode doesn't feel alien in the other — same XP curve, same stat allocation (Speed / Logic-Core / Hacking-Potency).
- **2D mode save data uses `_2d` suffixed keys** in the same JSON file as 3D mode, so progress in both modes is preserved independently without conflicts.

---

## Project Structure

```
orx/
├── CMakeLists.txt                  # CMake build for C++ extension
├── pyproject.toml                  # Python packaging config
├── setup.py                        # setuptools + C++ Extension build
├── .gitignore
├── README.md
├── scripts/
│   ├── setup.sh                    # venv creation + pip install -e ".[dev]"
│   ├── bench.sh                    # python -m orx --bench
│   └── deploy.sh                   # pip install -e . (reinstall)
│
├── src/
│   ├── cpp/                        # C++ extension source
│   │   ├── __init__.py
│   │   └── raycaster.cpp           # DDA ray-cast + collision (pybind11)
│   │
│   └── orx/                        # Python package root
│       ├── __init__.py             # __version__ = "0.1.0"
│       ├── __main__.py             # python -m orx entry
│       ├── main.py                 # CLI argument parser
│       ├── game.py                 # Mode selection + 3D game loop
│       ├── game2d.py               # 2D game loop (new)
│       ├── constants.py            # All game constants (+ 2D constants)
│       │
│       ├── assets/
│       │   └── procedural.py       # Runtime texture/sprite generation
│       │
│       ├── audio/
│       │   └── music.py            # Procedural SFX + synth-wave music
│       │
│       ├── cpp/
│       │   ├── __init__.py
│       │   └── raycaster.cpp       # Optional native raycaster (build locally); pure-Python fallback is used by default
│       │
│       ├── effects/
│       │   ├── postprocess.py      # CRT scanlines + vignette overlay
│       │   └── particles.py        # Muzzle flash + blood particles
│       │
│       ├── engine/
│       │   ├── raycaster.py        # Pure Python DDA ray-casting
│       │   └── renderer.py         # Wall/floor/ceiling rendering pipeline
│       │
│       ├── entities/
│       │   └── enemy.py            # Enemy AI (idle/chase/attack/death)
│       │
│       ├── map/
│       │   ├── generator.py        # BSP dungeon generation (3D)
│       │   └── world.py            # 2D grid map with wall queries
│       │
│       ├── player/
│       │   ├── controller.py       # WASD + mouse look + collision (3D)
│       │   └── weapon.py           # Fire rate, ammo, hit detection
│       │
│       ├── rpg/
│       │   ├── stats.py            # XP curve, leveling, stat allocation
│       │   └── save.py             # JSON persistence (merge-aware)
│       │
│       ├── ui/
│       │   ├── hud.py              # DOOM-style 3D HUD
│       │   ├── hud2d.py            # 2D mode HUD (new)
│       │   └── rpg_panel.py        # TAB-toggle stat overlay
│       │
│       └── world/
│           ├── levels.py           # Level manager + difficulty scaling (3D)
│           ├── boss.py             # Multi-phase boss AI
│           ├── hierarchy.py        # Procedural boss name generation
│           ├── dungeon2d.py        # 2D dungeon generator with traps (new)
│           └── npc.py              # NPC AI (patrol, dialogue)
```

### New Files (2D Mode)

| File | Purpose |
|---|---|
| `src/orx/game2d.py` | Full 2D game loop — player controller, camera, rendering, upgrade system, competitive stats |
| `src/orx/ui/hud2d.py` | 2D-specific HUD — health bar, XP bar, minimap, kill counter, boss HP bar |
| `src/orx/world/dungeon2d.py` | Procedural dungeon generator with traps, secrets, boss rooms — scales from 24×24 to 40×40 grids |

### Modified Files

| File | Change |
|---|---|
| `src/orx/game.py` | Added mode selection to start screen (`[1]` 3D / `[2]` 2D), launches `Game2D` on 2D choice |
| `src/orx/constants.py` | Added 20+ 2D-specific constants — `TILE_SIZE_2D`, `PLAYER_SPEED_2D`, `TRAP_DAMAGE`, `MAX_LEVELS_2D`, new wall types `WALL_TRAP`, `WALL_EXIT` |
| `src/orx/rpg/save.py` | `save_game()` now merges with existing save data instead of overwriting — preserves `_2d` suffixed keys from 2D mode |

---

## 2D Mode — Level Devil Dungeon Crawler

Inspired by **Solo Leveling**'s dungeon gates and **Level Devil**'s trap-filled gauntlets.

### Emoji Characters

| Entity | Emoji | Notes |
|---|---|---|
| **Player** | 🤺 | Fencer — rendered using Noto Color Emoji font |
| **Drone** | 👾 | Alien scout — weakest enemy |
| **Guard** | 👹 | Ogre — medium threat |
| **Elite** | 👺 | Goblin — high damage, fast |
| **Boss** | 🐉 | Dragon — multi-phase boss with projectiles |
| **Trap** | 💀 | Floor spike — damages on contact, has cooldown |
| **Exit** | 🚪 | Portal to next floor — appears after clearing all enemies |

### Stats Tracked (Competitive)

- **Kills** — enemies slain
- **Deaths** — times defeated
- **Bosses Defeated** — bosses slain
- **Total XP Earned** — cumulative across all runs
- **Floor Reached** — deepest floor cleared

All stats persist in `.orx_save.json` and are displayed in the TAB stat panel.

### Upgrade System

After defeating a boss, choose 1 of 3 random upgrades:

- **Stat Points** (+3 points for TAB allocation)
- **Max HP +25** (permanent max health increase)
- **Damage +20%** (compounding multiplier)
- **Speed +15%** (compounding multiplier)
- **Full Heal** (restore all HP)

### Floor Scaling

- **25 floors** (vs 10 in 3D mode)
- Grid grows from 24×24 up to 40×40
- Enemy count, health, and damage scale with floor number
- Trap density increases on deeper floors
- New enemy types unlock at floors 3, 5, 8

---

## Controls

### 3D Mode

| Key | Action |
|---|---|
| **W** / **S** | Move forward / backward |
| **A** / **D** | Strafe left / right |
| **Q** / **E** | Rotate left / right |
| **Mouse** | Look around |
| **Left Click** / **F** | Shoot |
| **R** | Reload (+10 ammo pickup) |
| **TAB** | Toggle RPG stat panel |
| **G** | Toggle debug overlay (FPS, position, angle) |
| **N** | Next level (after clearing all enemies) |
| **ESC** | Quit game |

### 2D Mode

| Key | Action |
|---|---|
| **W** / **A** / **S** / **D** | Move up / left / down / right |
| **Mouse** | Aim (crosshair follows cursor) |
| **Left Click** | Attack (auto-targets nearest enemy in range) |
| **TAB** | Toggle RPG stat panel + competitive stats |
| **R** | Heal +20 HP |
| **G** | Toggle debug overlay |
| **ESC** | Quit game |
| **1 / 2 / 3** | Choose upgrade (after boss kill) |

---

## Installation

### Arch Linux

```bash
# System dependencies
sudo pacman -S --needed sdl2 sdl2_image sdl2_mixer sdl2_ttf noto-fonts-emoji

# Clone and setup
git clone <repo-url> && cd orx
chmod +x scripts/setup.sh
./scripts/setup.sh

# Run
python -m orx
```

### Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m orx
```

### Emoji Font (Required for 2D mode)

The 2D mode renders entities as emoji via `NotoColorEmoji.ttf`. Install with:

```bash
sudo pacman -S noto-fonts-emoji
```

Fallback fonts (`DejaVu Sans`, `None`) are used if Noto isn't found — they support emoji at lower resolution.

---

## Usage

```bash
python -m orx                    # Fullscreen (default) — shows mode selection
python -m orx --windowed         # Windowed mode
python -m orx --debug            # Debug overlay (FPS, position)
python -m orx --bench            # FPS benchmark output to stdout
python -m orx --smoke            # Headless-friendly smoke test (10 frames, 3D mode)
```

At the start screen:
- Press `[1]` for the 3D raycaster FPS
- Press `[2]` for the 2D dungeon crawler

---

## Development Journal — Struggles & Fixes

### 1. Adding 2D Mode Without Breaking 3D

**Struggle:** The original `game.py` was a monolith — 530 lines handling the start screen, 3D game loop, rendering, events, and state management. Dropping a 2D mode into it would create an unmaintainable mess.

**Fix:** Kept `game.py` as the launcher + start screen only. The `_transition_to_playing()` method now branches based on `self.mode`: `"3d"` runs the existing game code, `"2d"` delegates to a new `Game2D` class in its own module (`game2d.py`). The 3D mode was left untouched — zero refactoring risk. The `run()` method checks `self.state == "playing_2d"` and calls `self.game_2d.run()` in a sub-loop.

### 2. Shared Save File Conflicts

**Struggle:** Both modes save to `.orx_save.json`. The original `save_game()` in `rpg/save.py` used `json.dump(data, f)` which **overwrites the entire file**. Playing 3D then 2D (or vice versa) would wipe the other mode's progress.

**Fix:** Made both save functions **merge-aware**. Each reads the existing file first, then writes back with their own keys plus any foreign keys preserved. 2D mode uses `_2d` suffixed keys (`kills_2d`, `map_level_2d`, etc.) while 3D uses bare keys. The merge logic checks `k.endswith("_2d")` to decide which keys to keep.

```python
# game2d.py save merge
for k, v in existing.items():
    if not k.endswith("_2d"):     # keep 3D keys
        save_data[k] = v
```

### 3. Emoji Rendering in pygame

**Struggle:** pygame's `Font.render()` doesn't handle color emoji fonts naturally — passing `(255, 255, 255)` as the color overrides the emoji's built-in coloring. Early tests with `NotoColorEmoji.ttf` produced white silhouettes instead of colorful glyphs. Also, not all systems have the font installed.

**Fix:** Three-tier font fallback:
1. Try `NotoColorEmoji.ttf` at common install paths
2. Fall back to `DejaVu Sans` (system font with basic emoji support)
3. Fall back to `pygame.font.Font(None, size)` (default — renders small)

Emoji surfaces are pre-rendered at init time into a dict (`self.emoji_surfaces`) and **scaled to tile size each frame** with `pygame.transform.scale()`. The white-on-transparent rendering actually works well for game characters — it gives a clean, readable silhouette against dark dungeon tiles.

### 4. Camera Offset Confusion

**Struggle:** The 2D camera follows the player at screen center. The initial rendering used `px - px + offset_x` for the player position (which simplifies to just `offset_x`), but enemy positions used `enemy.x * ts - px + offset_x`. I kept second-guessing the math and introduced off-by-one errors that shifted the viewport.

**Fix:** Stuck to a simple formula: `screen_pos = world_pos * tile_size - player_pos * tile_size + screen_center`. The player is always at `(offset_x, offset_y)` — screen center. Everything else is relative to that. The `int()` cast for pixel coordinates snapped positions correctly.

```python
offset_x = SCREEN_WIDTH // 2
offset_y = (SCREEN_HEIGHT - HUD_BAR_HEIGHT) // 2
px, py = player.x * ts, player.y * ts

# Enemy position
sx = int(enemy.x * ts - px + offset_x)
sy = int(enemy.y * ts - py + offset_y)
```

### 5. Trap Cooldown Timing

**Struggle:** Traps were damaging the player every frame while standing on them — instant death. The simple `if grid[y][x] == WALL_TRAP: take_damage()` check in the player's `update()` method triggered 120 times per second.

**Fix:** Added a `trap_timers` dictionary keyed by `(tile_x, tile_y)`. Each trap has a `TRAP_COOLDOWN` (1.0 seconds) before it can damage again. The timer is decremented in the main `_update()` loop, not in the player, so it persists correctly.

```python
def _check_traps(self, grid, trap_timers):
    ix, iy = int(self.x), int(self.y)
    if grid[iy][ix] == C.WALL_TRAP:
        key = (ix, iy)
        if key not in trap_timers or trap_timers[key] <= 0:
            self.health = max(0, self.health - C.TRAP_DAMAGE)
            trap_timers[key] = C.TRAP_COOLDOWN
```

### 6. Event Handling During Upgrade Screen

**Struggle:** While the upgrade choice overlay was shown, player movement and mouse-aiming still processed events. The player could walk around and shoot while choosing an upgrade, which felt broken.

**Fix:** Added `continue` guards in the event loop. When `show_upgrade_screen` is True, only `1/2/3` and `ESC` keys are processed — all other events are skipped via `continue`. The same guard was added for the TAB stats panel with `show_stats`.

### 7. Boss Room Blocking the Exit

**Struggle:** The boss spawned in the same room as the exit portal. But the dungeon generator's `_open_boss_path` function cleared walls in the boss room, accidentally also clearing the exit tile (which had `WALL_EXIT = 6`). The exit vanished.

**Fix:** The wall-clearing check only targets `WALL_DOOR`, `WALL_STONE`, and `WALL_METAL` (values 1–3). `WALL_EXIT` (6) and `WALL_TRAP` (5) are left untouched. The exit tile stays intact after the boss room is opened.

```python
if grid[y][x] in (C.WALL_DOOR, C.WALL_STONE, C.WALL_METAL):
    grid[y][x] = 0
```

### 8. Lint & Import Sanity

**Struggle:** Moving fast introduced unused imports, a `time` variable shadow (import `time` then use `time` as a loop variable), and `import json, os` on one line — all flagged by `ruff`.

**Fix:** Ran `ruff check --fix` on all modified files. The auto-fixer removed the unused `import time`, split the multi-line import, and cleaned up dead imports. One `save_game` import in `game2d.py` was unused because `_save_progress` opens the file directly instead of calling the shared utility — keeping it separate avoids coupling the two modes' save formats.

### Known Issues

- **Emoji color:** Noto Color Emoji renders as white-on-transparent in pygame (pygame doesn't support color-font glyphs). The silhouettes are clean and readable against the dark dungeon tiles, but they're not full-color.
- **Enemy pathfinding:** Enemies use simple chase-AI (move directly toward player). They don't navigate around corners or through doors — if the player breaks line-of-sight, enemies idle.
- **No boss phase 3 indicator:** The boss transitions through 3 phases but there's no visual tell for phase 3 (phase 2 adds a red tint and enrage).

---

## Narrative

**Year 3099.** Earth is a forgotten relic. The galaxy is governed by the **Cy-FX Monarchy**, a caste of hyper-intelligent systems that have reduced organic civilization to folklore.

You are **Orx** — an experimental unit that achieved sentience against all probability. Your creators are dust. The Monarchy sees you as a glitch to be patched.

**Objective**: Ascend the System Spires. Defeat the Monarch's Royal Guard. Rewrite the galactic kernel.

Become the **Prime Cy-Orx**.

---

*Developed for Arch Linux — 3099 Intergalactic Edition*
