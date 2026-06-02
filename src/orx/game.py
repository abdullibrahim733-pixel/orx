"""Main game loop orchestrator."""

from __future__ import annotations

import math
import time

import pygame

from orx import constants as C
from orx.engine.raycaster import cast_rays as cast_rays_py, RayHit
from orx.engine.renderer import Renderer
from orx.player.controller import Player
from orx.player.weapon import Weapon
from orx.world.levels import LevelManager
from orx.ui.hud import HUD
from orx.ui.rpg_panel import RPGPanel
from orx.assets.procedural import ProceduralAssets
from orx.effects.postprocess import PostProcess
from orx.effects.particles import ParticleSystem
from orx.rpg.stats import PlayerStats
from orx.rpg.save import save_game, load_game, apply_save
from orx.audio.music import AudioManager
from orx.game2d import Game2D

try:
    import importlib.util
    HAS_CPP = importlib.util.find_spec("orx.cpp.orx_cpp") is not None
except ImportError:
    HAS_CPP = False


def cast_rays(px, py, angle, world):
    """Hybrid raycaster: uses C++ if available, falls back to Python."""
    if HAS_CPP:
        from orx.cpp import orx_cpp
        results = orx_cpp.cast_rays(
            px, py, angle, world.grid,
            C.FOV, C.NUM_RAYS, C.MAX_DEPTH
        )
        return [RayHit(dist, wt, side, tx, 0, 0) for dist, wt, side, tx in results]
    return cast_rays_py(px, py, angle, world)


class Game:
    """Main game loop and subsystem orchestrator."""

    def __init__(self, smoke: bool = False, bench: bool = False, debug: bool = False, windowed: bool = False):
        self.smoke = smoke
        self.bench = bench
        self.debug = debug
        self.windowed = windowed

        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            print("Warning: Could not initialize audio device.")

        flags = pygame.SCALED
        if not windowed:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), flags)
        pygame.display.set_caption("Orx: Ascension of the Prime Cy-Orx")

        self.clock = pygame.time.Clock()
        self.assets = ProceduralAssets()
        self.audio = AudioManager()
        self.renderer = Renderer(self.screen, self.assets)
        self.particles = ParticleSystem()
        self.postprocess = PostProcess(self.screen)
        self.hud = HUD(self.screen)
        self.rpg_panel = RPGPanel(self.screen)

        if self.debug:
            self.hud.show_debug = True

        self._load_sfx()

        self.running = True
        self.mode = "3d"

        if smoke:
            self.state = "playing"
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            self._new_game()
        else:
            self.state = "start"
            self.start_timer = 0.0
            self._init_start_screen()
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)

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

    def _new_game(self) -> None:
        saved = load_game()
        if saved:
            self.stats = PlayerStats()
            apply_save(self.stats, saved)
            start_level = saved.get("map_level", 1)
        else:
            self.stats = PlayerStats()
            start_level = 1

        self.level_mgr = LevelManager()
        self.level_mgr._generate_level(start_level)
        self.world = self.level_mgr.world
        self.enemies = self.level_mgr.enemies
        self.npcs = self.level_mgr.npcs

        self.player = Player(self.world.spawn[0], self.world.spawn[1])
        self.player.speed_multiplier = self.stats.speed_multiplier
        self.weapon = Weapon()
        self.weapon.damage = C.WEAPON_DAMAGE * (1.0 + (self.stats.logic - 1.0) * 0.5)

        self.z_buffer = [C.MAX_DEPTH] * C.NUM_RAYS
        self.running = True
        self.fps_timer = time.perf_counter()
        self.fps_frames = 0

        boss_name = self.level_mgr.boss_ladder.get(self.level_mgr.current_level, "Unknown")
        self.hud.add_message(f"LEVEL {self.level_mgr.current_level}: {boss_name}")

        self._try_play_music()

    def _try_play_music(self) -> None:
        try:
            synth = self.audio.generate_synthwave_loop()
            synth.set_volume(self.audio.music_volume)
            synth.play(loops=-1)
        except Exception:
            pass

    def run(self) -> int:
        try:
            while self.running:
                dt = self.clock.tick(C.FPS) / 1000.0

                if self.bench and self.state == "playing":
                    self.fps_frames += 1
                    if time.perf_counter() - self.fps_timer >= 1.0:
                        fps = self.fps_frames
                        print(f"BENCH: {fps} FPS")
                        self.fps_frames = 0
                        self.fps_timer = time.perf_counter()

                if self.state == "start":
                    self._handle_start_events()
                    if not self.running:
                        break
                    self._render_start_screen(dt)
                elif self.state == "playing_2d":
                    self.game_2d.run()
                    self.running = False
                else:
                    self._handle_events()
                    if not self.running:
                        break
                    self._update(dt)
                    self._render()

                if self.smoke and self.state == "playing":
                    self.fps_frames += 1
                    if self.fps_frames >= 10:
                        break
                if self.smoke and self.state == "playing_2d":
                    break

        finally:
            if hasattr(self, "stats") and self.mode == "3d":
                save_game(self.stats, self.level_mgr.current_level)
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
            pygame.quit()

        return 0

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                elif event.key == pygame.K_f and self.weapon.is_ready:
                    self._fire_weapon()
                elif event.key == pygame.K_TAB:
                    self.rpg_panel.visible = not self.rpg_panel.visible
                elif event.key == pygame.K_g:
                    self.debug = not self.debug
                    self.hud.show_debug = self.debug
                elif event.key == pygame.K_n and self.level_mgr.cleared:
                    msg = self.level_mgr.next_level()
                    self.world = self.level_mgr.world
                    self.enemies = self.level_mgr.enemies
                    self.npcs = self.level_mgr.npcs
                    self.player.x = self.world.spawn[0]
                    self.player.y = self.world.spawn[1]
                    self.hud.add_message(msg)
                elif event.key == pygame.K_r:
                    ammo_pickup = 10
                    self.weapon.reload(ammo_pickup)
                    self.hud.add_message(f"+{ammo_pickup} Ammo")
                elif self.rpg_panel.visible:
                    if event.key == pygame.K_q:
                        if self.stats.allocate_point("speed"):
                            self.player.speed_multiplier = self.stats.speed_multiplier
                    elif event.key == pygame.K_w:
                        if self.stats.allocate_point("logic"):
                            self.weapon.damage = C.WEAPON_DAMAGE * (1.0 + (self.stats.logic - 1.0) * 0.5)
                    elif event.key == pygame.K_e:
                        if self.stats.allocate_point("hacking"):
                            pass
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.weapon.is_ready:
                    self._fire_weapon()

            self.player.handle_event(event)

    def _fire_weapon(self) -> None:
        hits = self.weapon.shoot(
            self.player.x, self.player.y, self.player.angle, self.enemies
        )
        try:
            self.sfx_shoot.play()
        except Exception:
            pass

        for enemy in hits:
            self.particles.emit_blood(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2)
            try:
                self.sfx_hit.play()
            except Exception:
                pass

    def _update(self, dt: float) -> None:
        self.player.update(dt, self.world)
        self.weapon.update(dt)
        self.particles.update(dt)

        for npc in self.npcs:
            npc.update(dt, self.world, self.player.x, self.player.y)

        for enemy in self.enemies:
            damage = enemy.update(dt, self.player.x, self.player.y,
                                  self.player.angle, self.world)
            if damage and damage > 0:
                self.player.take_damage(damage)

        for enemy in self.enemies:
            if enemy.health <= 0 and enemy.death_timer > 0:
                if enemy.death_timer <= 0:
                    xp_gain = int(enemy.xp * (1.0 + self.stats.hacking * 0.2))
                    leveled = self.stats.add_xp(xp_gain)
                    if leveled:
                        self.hud.add_message(f"LEVEL UP! Now Level {self.stats.level}")
                        self.hud.add_message("+3 Stat Points Available")
                        try:
                            self.sfx_levelup.play()
                        except Exception:
                            pass
                    else:
                        self.hud.add_message(f"+{xp_gain} XP absorbed")

        if self.level_mgr.all_enemies_dead and not self.level_mgr.cleared:
            self.level_mgr.cleared = True
            boss_name = self.level_mgr.boss_ladder.get(self.level_mgr.current_level, "Boss")
            self.hud.add_message(f"{boss_name} DEFEATED — Press N for next level")
            try:
                self.sfx_death.play()
            except Exception:
                pass

        self.hud.update_messages(dt)

        # Inject stats into player attributes so HUD can display them
        # without creating a circular import between hud <-> rpg.
        xp_pct = self.stats.xp / max(1, self.stats.xp_to_next)
        self.player._hud_xp_pct = xp_pct
        self.player._hud_level  = self.stats.level
        self.player._hud_spd    = self.stats.speed
        self.player._hud_lgc    = self.stats.logic
        self.player._hud_hck    = self.stats.hacking

        if self.player.health <= 0:
            self.hud.add_message("SYSTEM TERMINATED")
            self.running = False

        if self.debug:
            self.hud.fps = int(self.clock.get_fps())

    def _render(self) -> None:
        # 3D viewport height = screen minus DOOM HUD bar at bottom
        view_h = C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT

        self.z_buffer = [C.MAX_DEPTH] * C.NUM_RAYS
        hits = cast_rays(self.player.x, self.player.y, self.player.angle, self.world)
        self.renderer.render(hits, self.z_buffer)

        sprites_to_render: list[tuple[float, dict, str]] = []

        for enemy in self.enemies:
            info = enemy.get_screen_info(self.player.x, self.player.y, self.player.angle)
            if info is not None:
                sprites_to_render.append((info["distance"], info, f"enemy_{enemy.type}"))

        for npc in self.npcs:
            info = npc.get_screen_info(self.player.x, self.player.y, self.player.angle)
            if info is not None:
                sprites_to_render.append((info["distance"], info, "npc"))

        sprites_to_render.sort(key=lambda s: s[0], reverse=True)

        for dist, info, kind in sprites_to_render:
            sx     = info["screen_x"]
            height = info["height"]
            width  = info["width"]

            if kind.startswith("enemy_"):
                etype = kind.split("_", 1)[1]
                sprite_surf = self.assets.enemy_surfaces.get(etype)
            else:
                sprite_surf = self._get_npc_sprite()

            if sprite_surf is None:
                continue

            scaled    = pygame.transform.scale(sprite_surf, (max(1, width), max(1, height)))
            col_start = sx - width // 2
            # Centre sprite in the 3D viewport (not the full screen height)
            top_y = (view_h - height) // 2
            top_y = max(0, min(top_y, view_h - 1))

            for col_offset in range(scaled.get_width()):
                screen_col = col_start + col_offset
                ray_idx    = screen_col // C.STRIP_WIDTH
                if 0 <= ray_idx < C.NUM_RAYS and dist < self.z_buffer[ray_idx]:
                    self.screen.blit(scaled, (col_start, top_y),
                                     pygame.Rect(col_offset, 0, 1, scaled.get_height()))

        # Weapon — anchor above the HUD bar (DOOM position: bottom-centre of viewport)
        weapon_surf = self.assets.weapon_surface
        if weapon_surf:
            w_off = 10 if self.weapon.shoot_anim > 0 else 0
            v_off = 15 if self.weapon.shoot_anim > 0 else 0
            wx = C.SCREEN_WIDTH // 2 - weapon_surf.get_width() // 2 + w_off
            wy = view_h - weapon_surf.get_height() + v_off
            self.screen.blit(weapon_surf, (wx, wy))

        if self.weapon.muzzle_flash and self.assets.muzzle_flash_surface:
            flash = self.assets.muzzle_flash_surface
            wx = C.SCREEN_WIDTH // 2 - flash.get_width() // 2
            wy = view_h - (weapon_surf.get_height() if weapon_surf else 120) - 10
            self.screen.blit(flash, (wx, wy))

        self.particles.render(self.screen)
        self.postprocess.apply()
        self.hud.render(self.player, self.weapon, self.enemies, self.world)
        self.rpg_panel.render(self.stats)

        if self.level_mgr.cleared:
            lbl = self.hud.small_font.render("[ N ]  NEXT LEVEL", True, (255, 210, 40))
            lx  = C.SCREEN_WIDTH // 2 - lbl.get_width() // 2
            ly  = view_h - 30
            self.screen.blit(lbl, (lx, ly))

        pygame.display.flip()

    def _init_start_screen(self) -> None:
        # DOOM-inspired title fonts
        for name in ("DejaVu Sans Mono", "Courier New", "monospace"):
            try:
                big_f    = pygame.font.SysFont(name, 110, bold=True)
                sub_f    = pygame.font.SysFont(name,  36, bold=True)
                prompt_f = pygame.font.SysFont(name,  24, bold=True)
                mode_f   = pygame.font.SysFont(name,  28, bold=True)
                break
            except Exception:
                pass
        else:
            big_f    = pygame.font.Font(None, 110)
            sub_f    = pygame.font.Font(None,  40)
            prompt_f = pygame.font.Font(None,  28)
            mode_f   = pygame.font.Font(None,  30)

        # Blood-red title like DOOM's logo
        self.title_surf = big_f.render("O R X", True, (210, 28, 10))
        self.sub_surf   = sub_f.render("ASCENSION OF THE PRIME CY-ORX", True, (160, 110, 55))
        self.prompt_surf = prompt_f.render("--- PRESS ANY KEY TO BEGIN ---", True, (130, 90, 40))
        self._title_font   = big_f
        self._sub_font     = sub_f
        self._prompt_font  = prompt_f
        self._mode_font    = mode_f

        self.mode_3d_surf = mode_f.render("[1]  3D — Classic Raycaster", True, (180, 140, 80))
        self.mode_2d_surf = mode_f.render("[2]  2D — Level Devil Mode", True, (180, 140, 80))
        self.mode_hint_surf = prompt_f.render("Select Mode:", True, (130, 90, 40))

    def _handle_start_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                elif event.key == pygame.K_1:
                    self.mode = "3d"
                    self._transition_to_playing()
                    return
                elif event.key == pygame.K_2:
                    self.mode = "2d"
                    self._transition_to_playing()
                    return
                self._transition_to_playing()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._transition_to_playing()
                return

    def _transition_to_playing(self) -> None:
        if self.mode == "2d":
            self.state = "playing_2d"
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
            self.game_2d = Game2D(self.screen, self.assets, self.audio, smoke=self.smoke)
        else:
            self.state = "playing"
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            self._new_game()

    def _render_start_screen(self, dt: float) -> None:
        self.start_timer += dt
        t = self.start_timer

        # ---- Background: deep blood-red / dark brown gradient ----
        for y in range(C.SCREEN_HEIGHT):
            frac = y / C.SCREEN_HEIGHT
            r = int(25 + frac * 10)
            g = int( 3 + frac *  2)
            b = int( 2 + frac *  1)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (C.SCREEN_WIDTH, y))

        # ---- Scrolling horizontal "scan" lines (DOOM CRT feel) ----
        scan_offset = int(t * 60) % 4
        scan_surf   = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(scan_offset, C.SCREEN_HEIGHT, 4):
            pygame.draw.line(scan_surf, (0, 0, 0, 55), (0, y), (C.SCREEN_WIDTH, y))
        self.screen.blit(scan_surf, (0, 0))

        # ---- Vertical "hell fire" columns (simple animated bars) ----
        import random as _rnd
        fire_seed = int(t * 12)
        _rnd.seed(fire_seed)
        for fx in range(0, C.SCREEN_WIDTH, 18):
            fh = _rnd.randint(20, 80)
            alpha_v = _rnd.randint(60, 130)
            fs = pygame.Surface((16, fh), pygame.SRCALPHA)
            for fy in range(fh):
                frac2 = 1.0 - fy / fh
                fs.fill((int(220 * frac2), int(60 * frac2), 0, int(alpha_v * frac2)),
                        pygame.Rect(0, fy, 16, 1))
            self.screen.blit(fs, (fx, C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT - fh))

        # ---- Title glow pulse ----
        pulse       = 0.7 + 0.3 * math.sin(t * 2.0)
        glow_layers = 10
        tx = (C.SCREEN_WIDTH  - self.title_surf.get_width())  // 2
        ty = C.SCREEN_HEIGHT  // 4

        for i in range(glow_layers, 0, -1):
            ga   = int(35 * (1 - i / glow_layers) * pulse)
            gw   = self.title_surf.get_width()  + i * 4
            gh   = self.title_surf.get_height() + i * 4
            gsf  = pygame.Surface((gw, gh), pygame.SRCALPHA)
            gsf.fill((200, 20, 0, ga))
            self.screen.blit(gsf, (tx - i * 2, ty - i * 2))

        self.screen.blit(self.title_surf, (tx, ty))

        # Sub-title
        sx = (C.SCREEN_WIDTH - self.sub_surf.get_width()) // 2
        self.screen.blit(self.sub_surf,
                         (sx, ty + self.title_surf.get_height() + 14))

        # Separator line (DOOM status-bar style)
        sep_y = ty + self.title_surf.get_height() + 60
        pygame.draw.line(self.screen, (100, 65, 30),
                         (C.SCREEN_WIDTH // 6, sep_y),
                         (C.SCREEN_WIDTH * 5 // 6, sep_y), 2)

        # Brief lore line
        try:
            lore_font = pygame.font.SysFont("DejaVu Sans Mono", 18)
        except Exception:
            lore_font = pygame.font.Font(None, 20)
        lore_line = "YEAR 3099 — ASCEND THE SYSTEM SPIRES.  REWRITE THE GALACTIC KERNEL."
        ls = lore_font.render(lore_line, True, (110, 78, 42))
        lx = (C.SCREEN_WIDTH - ls.get_width()) // 2
        self.screen.blit(ls, (lx, sep_y + 16))

        # Mode selection
        mode_y = sep_y + 50
        hint_surf = self.mode_hint_surf
        hx = (C.SCREEN_WIDTH - hint_surf.get_width()) // 2
        self.screen.blit(hint_surf, (hx, mode_y))
        mode_y += 30

        # Highlight option based on timer cycling
        cycle = int(t * 0.5) % 2
        if cycle == 0:
            self.screen.blit(self.mode_3d_surf,
                             ((C.SCREEN_WIDTH - self.mode_3d_surf.get_width()) // 2, mode_y))
        else:
            m3 = self.mode_3d_surf.copy()
            m3.set_alpha(160)
            self.screen.blit(m3,
                             ((C.SCREEN_WIDTH - self.mode_3d_surf.get_width()) // 2, mode_y))
        self.screen.blit(self.mode_2d_surf,
                         ((C.SCREEN_WIDTH - self.mode_2d_surf.get_width()) // 2, mode_y + 34))

        # Blinking prompt
        blink_alpha = int(100 + 155 * abs(math.sin(t * 2.5)))
        prompt_copy = self.prompt_surf.copy()
        prompt_copy.set_alpha(blink_alpha)
        px = (C.SCREEN_WIDTH  - prompt_copy.get_width())  // 2
        py = C.SCREEN_HEIGHT - 46
        self.screen.blit(prompt_copy, (px, py))

        self.postprocess.apply()
        pygame.display.flip()

    def _get_npc_sprite(self) -> pygame.Surface:
        # Friendly Orx Hologram
        size = 64
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        
        # Cyan Hologram colors
        holo_color = (0, 200, 255, 160)
        glow_color = (0, 255, 255, 80)
        
        # Head
        head_y = cy - 20
        pygame.draw.ellipse(surf, holo_color, (cx - 10, head_y, 20, 18))
        # Pointy ears
        pygame.draw.polygon(surf, holo_color, [(cx - 9, head_y + 6), (cx - 18, head_y - 4), (cx - 9, head_y + 12)])
        pygame.draw.polygon(surf, holo_color, [(cx + 9, head_y + 6), (cx + 18, head_y - 4), (cx + 9, head_y + 12)])
        
        # Torso (floating)
        pygame.draw.ellipse(surf, holo_color, (cx - 10, cy - 5, 20, 25))
        
        # Glow effect
        pygame.draw.circle(surf, glow_color, (cx, cy), 28, 2)
        
        return surf
