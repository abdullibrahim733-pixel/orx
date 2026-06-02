"""2D top-down game mode — Level Devil meets Solo Leveling."""

from __future__ import annotations

import math
import random
import time

import pygame

from orx import constants as C
from orx.rpg.stats import PlayerStats
from orx.rpg.save import load_game, apply_save
from orx.audio.music import AudioManager
from orx.assets.procedural import ProceduralAssets
from orx.ui.hud2d import HUD2D
from orx.ui.shop_ui import ShopUI
from orx.rpg.shop import ShopManager
from orx.world.dungeon2d import generate_dungeon_2d
from orx.world.hierarchy import generate_boss_ladder
from orx.entities.enemy import Enemy
from orx.world.boss import BossAI


class Player2D:
    def __init__(self, spawn_x: float, spawn_y: float):
        self.x = spawn_x
        self.y = spawn_y
        self.angle = 0.0
        self.health = C.PLAYER_HEALTH_START
        self.max_health = C.PLAYER_HEALTH_MAX
        self.speed_multiplier = 1.0
        self.damage_multiplier = 1.0
        self.attack_cooldown = 0.0
        self._move_x = 0.0
        self._move_y = 0.0

    @property
    def speed(self) -> float:
        return C.PLAYER_SPEED_2D * self.speed_multiplier

    @property
    def attack_range(self) -> float:
        return C.ATTACK_RANGE_2D

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._move_y = -1
            elif event.key == pygame.K_DOWN:
                self._move_y = 1
            elif event.key == pygame.K_LEFT:
                self._move_x = -1
            elif event.key == pygame.K_RIGHT:
                self._move_x = 1
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                self._move_y = 0
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._move_x = 0
        elif event.type == pygame.MOUSEMOTION:
            dx = event.rel[0]
            dy = event.rel[1]
            if dx != 0 or dy != 0:
                self.angle = math.atan2(dy, dx)

    def update(self, dt: float, world_grid: list, trap_timers: dict) -> None:
        self.attack_cooldown = max(0, self.attack_cooldown - dt)

        dir_x = 0.0
        dir_y = 0.0
        if self._move_x != 0 or self._move_y != 0:
            length = math.hypot(self._move_x, self._move_y)
            dir_x = self._move_x / length
            dir_y = self._move_y / length

        mx, my = pygame.mouse.get_pos()
        cx, cy = C.SCREEN_WIDTH // 2, (C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT) // 2
        self.angle = math.atan2(my - cy, mx - cx)

        steps = 4
        step_dt = dt / steps
        for _ in range(steps):
            step_x = dir_x * self.speed * step_dt
            step_y = dir_y * self.speed * step_dt
            r = C.PLAYER_RADIUS_2D / C.TILE_SIZE_2D + 0.1

            new_x = self.x + step_x
            if not self._is_wall(new_x, self.y, world_grid, r):
                self.x = new_x
            new_y = self.y + step_y
            if not self._is_wall(self.x, new_y, world_grid, r):
                self.y = new_y

        self._check_traps(world_grid, trap_timers)

    def _is_wall(self, x: float, y: float, grid: list, r: float) -> bool:
        for dy in (-r, r):
            for dx in (-r, r):
                ix, iy = int(x + dx), int(y + dy)
                if iy < 0 or iy >= len(grid) or ix < 0 or ix >= len(grid[0]):
                    return True
                if grid[iy][ix] in (C.WALL_STONE, C.WALL_METAL, C.WALL_DOOR, C.WALL_SECRET):
                    return True
        return False

    def _check_traps(self, grid: list, trap_timers: dict) -> None:
        ix, iy = int(self.x), int(self.y)
        if iy < 0 or iy >= len(grid) or ix < 0 or ix >= len(grid[0]):
            return
        if grid[iy][ix] == C.WALL_TRAP:
            key = (ix, iy)
            if key not in trap_timers or trap_timers[key] <= 0:
                self.health = max(0, self.health - C.TRAP_DAMAGE)
                trap_timers[key] = C.TRAP_COOLDOWN

    def take_damage(self, amount: float) -> None:
        reduced = max(1, amount - getattr(self, '_defense_bonus', 0))
        self.health = max(0, self.health - reduced)

    def can_attack(self) -> bool:
        return self.attack_cooldown <= 0

    def attack(self) -> None:
        self.attack_cooldown = C.ATTACK_COOLDOWN_2D

    def heal(self, amount: float) -> None:
        self.health = min(self.max_health, self.health + amount)

    def find_closest_enemy(self, enemies: list, boss: Enemy | None = None) -> Enemy | None:
        best = None
        best_dist = float('inf')
        all_enemies = list(enemies)
        if boss is not None and boss.is_alive:
            all_enemies.append(boss)
        for e in all_enemies:
            if not e.is_alive:
                continue
            d = math.hypot(e.x - self.x, e.y - self.y)
            if d < best_dist:
                best_dist = d
                best = e
        if best is not None and best_dist <= self.attack_range / C.TILE_SIZE_2D:
            return best
        return None


class Game2D:
    def __init__(self, screen: pygame.Surface, assets: ProceduralAssets,
                 audio: AudioManager, smoke: bool = False):
        self.screen = screen
        self.assets = assets
        self.audio = audio
        self.smoke = smoke
        self.clock = pygame.time.Clock()
        self.running = True

        self._load_sfx()

        self.font_large = pygame.font.SysFont("DejaVu Sans Mono", 36, bold=True)
        self.font_small = pygame.font.SysFont("DejaVu Sans Mono", 22, bold=True)

        self._init_emoji_fonts()

        self.kills = 0
        self.deaths = 0
        self.bosses_defeated = 0
        self.total_xp = 0
        self.start_time = time.time()
        self.score = 0

        self.trap_timers: dict = {}
        self.transition_timer = 0.0
        self.transition_text = ""
        self.show_stats = False
        self.show_shop = False
        self.shop_cycle_index = 0  # 0=game, 1=stats, 2=shop

        saved = load_game()
        self.stats = PlayerStats()
        if saved:
            apply_save(self.stats, saved)
            self.kills = saved.get("kills_2d", 0)
            self.deaths = saved.get("deaths_2d", 0)
            self.bosses_defeated = saved.get("bosses_2d", 0)
            self.total_xp = saved.get("total_xp_2d", 0)
            self.stats.gold = saved.get("gold_2d", 0)
            self.stats.inventory = list(saved.get("inventory_2d", []))
            self.stats.equipped = dict(saved.get("equipped_2d", {
                "weapon": None, "armor": None, "accessory": None,
            }))
            self.stats.perm_attack_bonus = saved.get("perm_attack_bonus_2d", 0)
            self.stats.perm_defense_bonus = saved.get("perm_defense_bonus_2d", 0)
            self.stats.perm_speed_bonus = saved.get("perm_speed_bonus_2d", 0.0)
            start_level = saved.get("map_level_2d", 1)
        else:
            start_level = 1

        self.boss_ladder = generate_boss_ladder(C.MAX_LEVELS_2D)
        self.current_level = start_level
        self.max_level = C.MAX_LEVELS_2D

        self._load_level(self.current_level)
        self._init_player()

        self.upgrade_choice: list[str] | None = None
        self.upgrade_timer = 0.0
        self.show_upgrade_screen = False

        self.hud = HUD2D(screen)
        self.shop_manager = ShopManager(player_level=self.stats.level)
        self.shop_ui = ShopUI(screen)
        self.hud.add_message(f"LEVEL {self.current_level}")

    def _load_sfx(self) -> None:
        try:
            self.sfx_shoot = self.audio.generate_shoot_sfx()
            self.sfx_hit = self.audio.generate_hit_sfx()
            self.sfx_levelup = self.audio.generate_levelup_sfx()
            self.sfx_death = self.audio.generate_death_sfx()
            self.sfx_shoot.set_volume(self.audio.sfx_volume)
            self.sfx_hit.set_volume(self.audio.sfx_volume)
            self.sfx_levelup.set_volume(self.audio.sfx_volume)
            self.sfx_death.set_volume(self.audio.sfx_volume)
        except Exception:
            pass

    def _init_emoji_fonts(self) -> None:
        emoji_size = 36
        self._emoji_font = None
        for path in ("/usr/share/fonts/noto/NotoColorEmoji.ttf",
                     "/usr/share/fonts/noto/NotoEmoji-Regular.ttf",
                     "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"):
            try:
                self._emoji_font = pygame.font.Font(path, emoji_size)
                break
            except Exception:
                continue
        if self._emoji_font is None:
            try:
                self._emoji_font = pygame.font.SysFont("DejaVu Sans", emoji_size)
            except Exception:
                self._emoji_font = pygame.font.Font(None, emoji_size)

        self.emoji_surfaces = {}
        emoji_map = {
            "player": "🤺",
            "drone":  "👾",
            "guard":  "👹",
            "elite":  "👺",
            "boss":   "🐉",
            "trap":   "💀",
            "exit":   "🚪",
            "health": "❤️",
            "skull":  "💀",
            "star":   "⭐",
        }
        for key, emoji in emoji_map.items():
            try:
                surf = self._emoji_font.render(emoji, True, (255, 255, 255))
                self.emoji_surfaces[key] = surf
            except Exception:
                self.emoji_surfaces[key] = None

    def _init_player(self) -> None:
        self.player = Player2D(self.world.spawn[0], self.world.spawn[1])
        self.player.speed_multiplier = self.stats.speed_multiplier + self.stats.perm_speed_bonus
        self.player.damage_multiplier = self.stats.damage_multiplier
        self.player._defense_bonus = self.stats.perm_defense_bonus
        self.player.health = C.PLAYER_HEALTH_START

    def _load_level(self, level: int) -> None:
        self.current_level = level
        seed = 999 + level * 37
        self.world = generate_dungeon_2d(seed=seed, level=level)
        self.grid = self.world.grid

        self.enemies = []
        pool = ["drone"]
        if level >= 2:
            pool.extend(["drone", "guard"])
        if level >= 5:
            pool.extend(["guard", "elite"])
        if level >= 10:
            pool.extend(["elite", "elite", "elite"])

        for ex, ey, _ in self.world.enemy_spawns[:-1]:
            etype = random.choice(pool)
            enemy = Enemy(ex, ey, etype)
            enemy.health = int(enemy.health * (1.0 + level * 0.15))
            enemy.damage = int(enemy.damage * (1.0 + level * 0.1))
            enemy.xp = int(enemy.xp * (1.0 + level * 0.1))
            self.enemies.append(enemy)

        self.boss = None
        if len(self.world.enemy_spawns) > 0:
            boss_data = self.world.enemy_spawns[-1]
            boss_name = self.boss_ladder.get(level, "Dungeon Lord")
            self.boss = BossAI(boss_data[0], boss_data[1], boss_name)
            self.boss.max_health = int(self.boss.max_health * (1.0 + level * 0.35))
            self.boss.health = self.boss.max_health
            self.boss.damage = int(self.boss.damage * (1.0 + level * 0.2))
            self.boss.phase_threshold = self.boss.max_health / self.boss.max_phases

        self.level_cleared = False
        self.exit_open = False
        self.transition_timer = 0.0
        self.trap_timers = {}

    def run(self) -> int:
        try:
            while self.running:
                dt = self.clock.tick(C.FPS) / 1000.0

                self._handle_events()
                if not self.running:
                    break

                if not self.show_upgrade_screen:
                    self._update(dt)
                else:
                    self._update_upgrade(dt)

                self._render()

                if self.smoke:
                    break

                self.hud.update_messages(dt)
        finally:
            self._save_progress()
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
        return 0

    def _save_progress(self) -> None:
        import json
        import os
        existing = {}
        if os.path.exists(".orx_save.json"):
            try:
                with open(".orx_save.json") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        save_data = {
            "level_2d": self.stats.level,
            "xp_2d": self.stats.xp,
            "xp_to_next_2d": self.stats.xp_to_next,
            "speed_2d": self.stats.speed,
            "logic_2d": self.stats.logic,
            "hacking_2d": self.stats.hacking,
            "stat_points_2d": self.stats.stat_points,
            "map_level_2d": self.current_level,
            "kills_2d": self.kills,
            "deaths_2d": self.deaths,
            "bosses_2d": self.bosses_defeated,
            "total_xp_2d": self.total_xp,
            "gold_2d": self.stats.gold,
            "inventory_2d": self.stats.inventory,
            "equipped_2d": self.stats.equipped,
            "perm_attack_bonus_2d": self.stats.perm_attack_bonus,
            "perm_defense_bonus_2d": self.stats.perm_defense_bonus,
            "perm_speed_bonus_2d": self.stats.perm_speed_bonus,
        }
        for k, v in existing.items():
            if not k.endswith("_2d"):
                save_data[k] = v
        with open(".orx_save.json", "w") as f:
            json.dump(save_data, f, indent=2)

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                elif event.key == pygame.K_TAB:
                    self._cycle_display_mode()
                elif event.key == pygame.K_g:
                    self.hud.show_debug = not self.hud.show_debug
                elif event.key == pygame.K_r:
                    self.player.heal(20)
                    self.hud.add_message("+20 HP")

            if self.show_upgrade_screen:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self._apply_upgrade(0)
                    elif event.key == pygame.K_2:
                        self._apply_upgrade(1)
                    elif event.key == pygame.K_3:
                        self._apply_upgrade(2)
                continue

            if self.show_stats:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q and self.stats.allocate_point("speed"):
                        self.player.speed_multiplier = self.stats.speed_multiplier
                    elif event.key == pygame.K_w and self.stats.allocate_point("logic"):
                        self.player.damage_multiplier = self.stats.damage_multiplier
                    elif event.key == pygame.K_e and self.stats.allocate_point("hacking"):
                        pass
                continue

            if self.show_shop:
                items = self.shop_manager.get_visible_items(self.stats.level)
                acted = self.shop_ui.handle_input(event, items)
                if acted:
                    self._handle_shop_purchase(items)
                if not self.show_shop:
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
                    self.show_shop = False
                    self.shop_ui.close()
                continue

            self.player.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.player.can_attack():
                    self._fire_weapon()

    def _cycle_display_mode(self) -> None:
        self.shop_cycle_index = (self.shop_cycle_index + 1) % 3
        self.show_stats = self.shop_cycle_index == 1
        if self.shop_cycle_index == 2:
            self.show_shop = True
            self.shop_ui.open()
            self.shop_manager.refresh_if_needed(self.bosses_defeated)
        else:
            self.show_shop = False
            self.shop_ui.close()

    def _handle_shop_purchase(self, items: list[dict]) -> None:
        if not items or self.shop_ui.selected_idx >= len(items):
            return
        item = items[self.shop_ui.selected_idx]
        item_id = item["item_id"]
        ok, msg = self.shop_manager.can_purchase(
            item_id, self.stats.gold, self.stats.level, len(self.stats.inventory)
        )
        if not ok:
            self.shop_ui.show_notification(msg, is_error=True)
            return

        bought = self.shop_manager.execute_purchase(item_id)
        if bought is None:
            self.shop_ui.show_notification("Purchase failed.", is_error=True)
            return

        self.stats.gold -= bought["purchase_cost"]
        inv_entry = {k: bought[k] for k in ("item_id", "name", "tier", "category", "modifiers")}
        self.stats.inventory.append(inv_entry)

        mods = bought.get("modifiers", {})
        if bought["category"] == "permanent":
            self.stats.perm_attack_bonus += mods.get("perm_attack", 0)
            self.stats.perm_defense_bonus += mods.get("perm_defense", 0)
            self.stats.perm_speed_bonus += mods.get("perm_speed", 0.0)
            self.player.speed_multiplier = self.stats.speed_multiplier + self.stats.perm_speed_bonus
            self.player._defense_bonus = self.stats.perm_defense_bonus
            self.player.damage_multiplier = self.stats.damage_multiplier  # attack handled in _fire_weapon

        self.shop_ui.show_notification(f"Purchased: {bought['name']}!")

    def _fire_weapon(self) -> None:
        self.player.attack()
        try:
            self.sfx_shoot.play()
        except Exception:
            pass

        target = self.player.find_closest_enemy(self.enemies, self.boss)
        if target is not None:
            dmg = C.WEAPON_DAMAGE * self.player.damage_multiplier
            dmg *= (1.0 + (self.stats.logic - 1.0) * 0.5)
            dmg += self.stats.perm_attack_bonus
            target.take_damage(dmg)
            try:
                self.sfx_hit.play()
            except Exception:
                pass
            if not target.is_alive:
                if target is self.boss:
                    self.bosses_defeated += 1
                    self.hud.add_message(f"BOSS DEFEATED: {self.boss.name}")
                else:
                    self.kills += 1
                self._award_xp(target)
                self._award_gold(target)

    def _award_gold(self, enemy: Enemy) -> None:
        gold = C.GOLD_PER_KILL_BASE + self.current_level * 5
        if enemy is self.boss:
            gold += C.GOLD_BOSS_BONUS
        self.stats.gold += gold
        self.hud.add_message(f"+{gold} Gold")

    def _award_xp(self, enemy: Enemy) -> None:
        xp_gain = int(enemy.xp * (1.0 + self.stats.hacking * 0.2))
        self.total_xp += xp_gain
        leveled = self.stats.add_xp(xp_gain)
        if leveled:
            self.hud.add_message(f"LEVEL UP! Now Level {self.stats.level}")
            self.hud.add_message("+3 Stat Points (TAB to assign)")
            try:
                self.sfx_levelup.play()
            except Exception:
                pass
        else:
            self.hud.add_message(f"+{xp_gain} XP")

    def _update(self, dt: float) -> None:
        self.weapon_cooldown = getattr(self, 'weapon_cooldown', 0.0)
        self.weapon_cooldown = max(0, self.weapon_cooldown - dt)

        for key in list(self.trap_timers.keys()):
            self.trap_timers[key] = max(0, self.trap_timers[key] - dt)
            if self.trap_timers[key] <= 0:
                del self.trap_timers[key]

        self.player.update(dt, self.grid, self.trap_timers)

        for enemy in self.enemies[:]:
            if enemy.is_alive:
                enemy.update(dt, self.player.x, self.player.y, self.player.angle, self.world)
                dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
                if dist < 0.5:
                    damage = getattr(enemy, 'damage', 5)
                    self.player.take_damage(damage)
            elif enemy.death_timer > 0:
                enemy.death_timer -= dt

        if self.boss is not None and self.boss.is_alive:
            dmg = self.boss.update(dt, self.player.x, self.player.y, self.player.angle, self.world)
            if dmg and dmg > 0:
                self.player.take_damage(dmg)
            dist = math.hypot(self.boss.x - self.player.x, self.boss.y - self.player.y)
            if dist < 0.6:
                self.player.take_damage(self.boss.damage * 0.5 * dt * 60)

        all_dead = all(not e.is_alive for e in self.enemies)
        boss_dead = self.boss is None or not self.boss.is_alive

        if all_dead and boss_dead and not self.level_cleared:
            self.level_cleared = True
            self.exit_open = True
            if self.boss is not None:
                self.hud.add_message(f"{self.boss.name} DEFEATED!")
                self._show_upgrade_choice()
            else:
                self.hud.add_message("LEVEL CLEARED!")

        if self.exit_open:
            if self._player_at_exit():
                self._next_level()

        xp_pct = self.stats.xp / max(1, self.stats.xp_to_next)
        self.player._hud_xp_pct = xp_pct
        self.player._hud_level = self.stats.level

        if self.player.health <= 0:
            self.deaths += 1
            self.hud.add_message("YOU DIED!")
            self.running = False

        if self.hud.show_debug:
            self.hud.fps = int(self.clock.get_fps())

    def _player_at_exit(self) -> bool:
        ex, ey = self.world.exit_pos
        dist = math.hypot(self.player.x - ex, self.player.y - ey)
        return dist < 1.0

    def _next_level(self) -> None:
        if self.current_level < self.max_level:
            self.current_level += 1
            self._load_level(self.current_level)
            self._init_player()
            boss_name = self.boss_ladder.get(self.current_level, "Unknown")
            self.hud.add_message(f"LEVEL {self.current_level}: {boss_name}")
            try:
                synth = self.audio.generate_synthwave_loop()
                synth.set_volume(self.audio.music_volume)
                synth.play(loops=-1)
            except Exception:
                pass
        else:
            self.hud.add_message("ALL LEVELS CLEARED — YOU WIN!")
            self.running = False

    def _show_upgrade_choice(self) -> None:
        choices = []
        if self.stats.stat_points > 0:
            choices.append("STAT POINTS")
        choices.extend([
            "MAX HP +25",
            "DAMAGE +20%",
            "SPEED +15%",
            "HEAL FULL",
        ])
        random.shuffle(choices)
        self.upgrade_choice = choices[:3]
        self.show_upgrade_screen = True
        self.upgrade_timer = 30.0

    def _update_upgrade(self, dt: float) -> None:
        self.upgrade_timer -= dt
        if self.upgrade_timer <= 0:
            self._dismiss_upgrade()

    def _apply_upgrade(self, index: int) -> None:
        if self.upgrade_choice is None or index >= len(self.upgrade_choice):
            return
        choice = self.upgrade_choice[index]
        if choice == "STAT POINTS":
            self.stats.stat_points += 3
            self.hud.add_message("+3 Stat Points!")
        elif choice == "MAX HP +25":
            self.player.max_health += 25
            self.player.heal(25)
            self.hud.add_message("Max HP +25!")
        elif choice == "DAMAGE +20%":
            self.player.damage_multiplier *= 1.2
            self.hud.add_message("Damage +20%!")
        elif choice == "SPEED +15%":
            self.player.speed_multiplier *= 1.15
            self.hud.add_message("Speed +15%!")
        elif choice == "HEAL FULL":
            self.player.heal(999)
            self.hud.add_message("Fully Healed!")
        self._dismiss_upgrade()

    def _dismiss_upgrade(self) -> None:
        self.show_upgrade_screen = False
        self.upgrade_choice = None

    def _render(self) -> None:
        self.screen.fill((0, 0, 0))

        if self.show_upgrade_screen:
            self._render_game_view()
            self._render_upgrade_overlay()
        else:
            self._render_game_view()
            self._render_hud()

        if self.show_stats and not self.show_upgrade_screen:
            self._render_stats_panel()

        if self.show_shop and not self.show_upgrade_screen:
            self.shop_ui.render(
                self.shop_manager.get_visible_items(self.stats.level),
                self.stats.gold, self.stats.level, self.stats
            )

        if self.exit_open:
            self._render_exit_marker()

        pygame.display.flip()

    def _render_game_view(self) -> None:
        ts = C.TILE_SIZE_2D
        offset_x = C.SCREEN_WIDTH // 2
        offset_y = (C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT) // 2
        px, py = self.player.x * ts, self.player.y * ts

        for gy in range(len(self.grid)):
            for gx in range(len(self.grid[0])):
                tile = self.grid[gy][gx]
                sx = int(gx * ts - px + offset_x)
                sy = int(gy * ts - py + offset_y)
                if sx < -ts or sx > C.SCREEN_WIDTH + ts or sy < -ts or sy > C.SCREEN_HEIGHT + ts:
                    continue

                if tile == 0:
                    color = (16, 14, 12)
                elif tile == C.WALL_STONE:
                    color = (60, 45, 30)
                elif tile == C.WALL_METAL:
                    color = (45, 50, 60)
                elif tile == C.WALL_DOOR:
                    color = (80, 55, 35)
                elif tile == C.WALL_SECRET:
                    color = (55, 42, 35)
                elif tile == C.WALL_TRAP:
                    color = (80, 20, 10)
                elif tile == C.WALL_EXIT:
                    color = (0, 180, 80)
                else:
                    color = (30, 30, 40)

                if tile == C.WALL_TRAP:
                    pulse = 0.6 + 0.4 * math.sin(time.time() * 3 + gx + gy)
                    color = tuple(int(c * pulse) for c in color)

                pygame.draw.rect(self.screen, color, (sx, sy, ts, ts))
                if tile != 0 and tile != C.WALL_TRAP and tile != C.WALL_EXIT:
                    pygame.draw.rect(self.screen, (0, 0, 0), (sx, sy, ts, ts), 1)

                if tile == C.WALL_TRAP:
                    trap_surf = self.emoji_surfaces.get("trap")
                    if trap_surf:
                        ts2 = ts - 4
                        ts2 = max(ts2, 8)
                        ts_emoji = pygame.transform.scale(trap_surf, (ts2, ts2))
                        ts_emoji.set_alpha(180)
                        self.screen.blit(ts_emoji, (sx + 2, sy + 2))

        for enemy in self.enemies:
            if not enemy.is_alive:
                continue
            sx = int(enemy.x * ts - px + offset_x)
            sy = int(enemy.y * ts - py + offset_y)
            emoji_key = enemy.type if enemy.type in self.emoji_surfaces else "drone"
            emoji_surf = self.emoji_surfaces.get(emoji_key)
            if emoji_surf:
                es = pygame.transform.scale(emoji_surf, (ts - 4, ts - 4))
                self.screen.blit(es, (sx + 2, sy + 2))
            hp_pct = enemy.health / max(1, enemy.max_health)
            bar_w = ts - 4
            pygame.draw.rect(self.screen, (40, 10, 10), (sx + 2, sy - 6, bar_w, 4))
            pygame.draw.rect(self.screen, (200, 30, 30), (sx + 2, sy - 6, int(bar_w * hp_pct), 4))

        if self.boss is not None and self.boss.is_alive:
            sx = int(self.boss.x * ts - px + offset_x)
            sy = int(self.boss.y * ts - py + offset_y)
            boss_surf = self.emoji_surfaces.get("boss")
            if boss_surf:
                bs = pygame.transform.scale(boss_surf, (ts + 8, ts + 8))
                self.screen.blit(bs, (sx - 4, sy - 4))
            hp_pct = self.boss.health / max(1, self.boss.max_health)
            bar_w = ts + 8
            pygame.draw.rect(self.screen, (40, 10, 10), (sx + 2 - 4, sy - 10, bar_w, 5))
            pygame.draw.rect(self.screen, (255, 50, 0), (sx + 2 - 4, sy - 10, int(bar_w * hp_pct), 5))
            phase_text = self.font_small.render(f"PHASE {self.boss.phase}", True, (255, 200, 0))
            self.screen.blit(phase_text, (sx - 10, sy - 28))

        psx = offset_x
        psy = offset_y
        player_surf = self.emoji_surfaces.get("player")
        if player_surf:
            ps = pygame.transform.scale(player_surf, (ts, ts))
            self.screen.blit(ps, (psx - ts // 2, psy - ts // 2))
        aim_x = psx + math.cos(self.player.angle) * 20
        aim_y = psy + math.sin(self.player.angle) * 20
        pygame.draw.line(self.screen, (255, 255, 100), (psx, psy), (aim_x, aim_y), 2)

    def _render_hud(self) -> None:
        self.hud.render(self.player, self.stats, self.enemies, self.boss, self.kills, self.current_level, self.grid)

    def _render_stats_panel(self) -> None:
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        x = C.SCREEN_WIDTH // 2 - 180
        y = 60

        title = self.font_large.render("/// ORX SYS-STATS ///", True, (220, 50, 10))
        self.screen.blit(title, (x + 20, y))
        y += 44

        font = self.font_small
        val_col = (215, 180, 60)
        dim_col = (130, 100, 60)
        hilight = (60, 220, 255)

        self._stat_row(f"LEVEL  {self.stats.level:>2}", x, y, val_col, font)
        y += 28
        xp_pct = self.stats.xp / max(1, self.stats.xp_to_next)
        pygame.draw.rect(self.screen, (10, 20, 50), (x + 10, y, 300, 10))
        pygame.draw.rect(self.screen, (60, 180, 255), (x + 10, y, int(300 * xp_pct), 10))
        pygame.draw.rect(self.screen, (100, 60, 40), (x + 10, y, 300, 10), 1)
        xp_lbl = font.render(f"XP  {self.stats.xp}/{self.stats.xp_to_next}", True, dim_col)
        self.screen.blit(xp_lbl, (x + 10, y + 14))
        y += 44

        pygame.draw.line(self.screen, (130, 85, 40), (x + 10, y), (x + 310, y), 1)
        y += 10

        sp_col = hilight if self.stats.stat_points > 0 else dim_col
        self._stat_row(f"STAT PTS  {self.stats.stat_points:>2}", x, y, sp_col, font)
        y += 32

        for label, value, key in [
            ("SPEED      [Q]", self.stats.speed, "speed"),
            ("LOGIC-CORE [W]", self.stats.logic, "logic"),
            ("HACKING    [E]", self.stats.hacking, "hacking"),
        ]:
            self._stat_row(f"{label}  {value:.1f}", x, y, val_col, font)
            y += 22
            pct = (value - 1.0) / 7.0
            pygame.draw.rect(self.screen, (40, 20, 10), (x + 20, y, 280, 8))
            pygame.draw.rect(self.screen, (180, 50, 10), (x + 20, y, int(280 * max(0, pct)), 8))
            pygame.draw.rect(self.screen, (100, 60, 40), (x + 20, y, 280, 8), 1)
            y += 18

        y += 8
        pygame.draw.line(self.screen, (130, 85, 40), (x + 10, y), (x + 310, y), 1)
        y += 12

        dmg_mult = 1.0 + (self.stats.logic - 1.0) * 0.5
        spd_mult = self.stats.speed
        xp_bonus = (self.stats.hacking - 1.0) * 20.0
        for label, val, unit in [
            ("DMG MULT", dmg_mult, "x"),
            ("SPD MULT", spd_mult, "x"),
            ("XP BONUS", xp_bonus, "%"),
        ]:
            self._stat_row(f"{label}  {val:+.1f}{unit}", x, y, dim_col, font)
            y += 24

        y += 16
        pygame.draw.line(self.screen, (130, 85, 40), (x + 10, y), (x + 310, y), 1)
        y += 10
        self._stat_row(f"KILLS   {self.kills}", x, y, (200, 180, 100), font)
        y += 22
        self._stat_row(f"DEATHS  {self.deaths}", x, y, (200, 100, 100), font)
        y += 22
        self._stat_row(f"BOSSES  {self.bosses_defeated}", x, y, (255, 200, 50), font)

    def _stat_row(self, text: str, x: int, y: int, color: tuple, font) -> None:
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _render_exit_marker(self) -> None:
        ts = C.TILE_SIZE_2D
        offset_x = C.SCREEN_WIDTH // 2
        offset_y = (C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT) // 2
        px, py = self.player.x * ts, self.player.y * ts
        ex, ey = self.world.exit_pos
        sx = int(ex * ts - px + offset_x)
        sy = int(ey * ts - py + offset_y)
        if -ts < sx < C.SCREEN_WIDTH + ts and -ts < sy < C.SCREEN_HEIGHT + ts:
            exit_surf = self.emoji_surfaces.get("exit")
            if exit_surf:
                pulse = 0.7 + 0.3 * math.sin(time.time() * 3)
                es = pygame.transform.scale(exit_surf, (ts + 4, ts + 4))
                es.set_alpha(int(pulse * 255))
                self.screen.blit(es, (sx - 2, sy - 2))
            else:
                pulse = 0.5 + 0.5 * math.sin(time.time() * 3)
                color = (0, int(200 * pulse), int(100 * pulse))
                pygame.draw.circle(self.screen, color, (sx + ts // 2, sy + ts // 2), ts // 2, 3)
            lbl = self.font_small.render("EXIT", True, (0, 255, 100))
            self.screen.blit(lbl, (sx - 10, sy - 20))

    def _render_upgrade_overlay(self) -> None:
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("CHOOSE YOUR UPGRADE", True, (255, 200, 50))
        tx = (C.SCREEN_WIDTH - title.get_width()) // 2
        self.screen.blit(title, (tx, 80))

        if self.upgrade_choice:
            for i, choice in enumerate(self.upgrade_choice):
                color = [(255, 100, 100), (100, 255, 100), (100, 100, 255)][i]
                key = f"[{i + 1}]"
                text = self.font_small.render(f"{key}  {choice}", True, color)
                tx = (C.SCREEN_WIDTH - text.get_width()) // 2
                ty = 180 + i * 50
                self.screen.blit(text, (tx, ty))

        timer_text = self.font_small.render(f"Time: {int(self.upgrade_timer)}s", True, (150, 150, 150))
        self.screen.blit(timer_text, (C.SCREEN_WIDTH // 2 - 40, 340))

        hint = self.font_small.render("Press 1/2/3 to choose", True, (120, 120, 120))
        hx = (C.SCREEN_WIDTH - hint.get_width()) // 2
        self.screen.blit(hint, (hx, 400))
