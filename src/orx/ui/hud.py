"""HUD rendering — DOOM-style status bar with Orx sci-fi skin."""

from __future__ import annotations

import math
import pygame
from orx import constants as C
from orx.player.controller import Player
from orx.player.weapon import Weapon
from orx.entities.enemy import Enemy
from orx.map.world import WorldMap


# ---------------------------------------------------------------------------
# Colour palette (DOOM-flavoured, Orx-themed)
# ---------------------------------------------------------------------------
_BAR_BG        = (28,  22,  18)   # very dark brown — status-bar background
_BAR_BORDER    = (80,  60,  40)   # warm brown border line
_PANEL_BG      = (20,  16,  12)   # recessed panels inside bar
_NUMBER_RED    = (220,  40,  10)   # DOOM digit red — ammo / health < 25 %
_NUMBER_GOLD   = (215, 185,  60)   # DOOM digit yellow-gold — normal
_NUMBER_GREEN  = ( 60, 210,  60)   # healthy
_LABEL_COLOR   = (160, 130,  90)   # dimmed label text
_FACE_BG       = ( 35,  28,  20)
_MINIMAP_BG    = (  0,   0,   0, 170)
_MSG_COLOR     = (255, 200,  50)
_XP_BAR_COLOR  = ( 80, 180, 255)
_XP_BG_COLOR   = ( 25,  25,  50)


def _load_doom_font(size: int) -> pygame.font.Font:
    """Return system font that feels chunky; falls back gracefully."""
    for name in ("DejaVu Sans Mono", "Courier New", "monospace"):
        try:
            f = pygame.font.SysFont(name, size, bold=True)
            if f:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, size)


class HUD:
    """Heads-up display — DOOM-style bottom bar + minimap + messages."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # Fonts
        self.num_font   = _load_doom_font(36)   # big stat numbers
        self.lbl_font   = _load_doom_font(16)   # tiny labels under numbers
        self.msg_font   = _load_doom_font(30)   # centre-screen messages
        self.small_font = _load_doom_font(18)   # debug / misc
        self.xp_font    = _load_doom_font(14)   # XP bar label

        self.messages: list[tuple[str, float]] = []
        self.fps      = 0
        self.show_debug = False

        self._bar_y = C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT
        self._bar_surf: pygame.Surface | None = None
        self._face_surfs: list[pygame.Surface] = []
        self._build_bar_background()
        self._build_face_sprites()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_message(self, text: str) -> None:
        self.messages.append((text, 3.0))

    def update_messages(self, dt: float) -> None:
        self.messages = [(t, time - dt) for t, time in self.messages if time - dt > 0]

    def render(self, player: Player, weapon: Weapon, enemies: list[Enemy],
               world: WorldMap) -> None:
        self._draw_crosshair()
        self._draw_status_bar(player, weapon)
        self._draw_minimap(player, world, enemies)
        self._draw_messages()
        if self.show_debug:
            self._draw_debug(player)

    # ------------------------------------------------------------------
    # Crosshair
    # ------------------------------------------------------------------

    def _draw_crosshair(self) -> None:
        cx = C.SCREEN_WIDTH // 2
        cy = self._bar_y // 2          # centre of the 3D view, above the bar
        gap, arm = 4, 9
        col = (220, 180, 60)
        pygame.draw.line(self.screen, col, (cx - gap - arm, cy), (cx - gap, cy), 2)
        pygame.draw.line(self.screen, col, (cx + gap, cy), (cx + gap + arm, cy), 2)
        pygame.draw.line(self.screen, col, (cx, cy - gap - arm), (cx, cy - gap), 2)
        pygame.draw.line(self.screen, col, (cx, cy + gap), (cx, cy + gap + arm), 2)
        # centre dot
        pygame.draw.circle(self.screen, col, (cx, cy), 2)

    # ------------------------------------------------------------------
    # Status bar (DOOM bottom bar)
    # ------------------------------------------------------------------

    def _build_bar_background(self) -> None:
        """Pre-render the static parts of the status bar."""
        w, h = C.SCREEN_WIDTH, C.HUD_BAR_HEIGHT
        surf = pygame.Surface((w, h))
        surf.fill(_BAR_BG)

        # Top separator line
        pygame.draw.line(surf, _BAR_BORDER, (0, 0), (w, 0), 2)

        # Three recessed panels: AMMO | FACE | HEALTH/ARMOR/XP
        # Panel rects (local coords inside surf)
        panels = [
            pygame.Rect(8,   6, 140, 68),   # left  – ammo + arms
            pygame.Rect(156, 6, 130, 68),   # face portrait
            pygame.Rect(294, 6, 300, 68),   # health / armor / XP
        ]
        for r in panels:
            # sunken panel fill
            pygame.draw.rect(surf, _PANEL_BG, r)
            # bevelled border (dark top-left, lighter bottom-right)
            pygame.draw.line(surf, (10,  8,  6),      r.topleft,     (r.right, r.top),   1)
            pygame.draw.line(surf, (10,  8,  6),      r.topleft,     (r.left,  r.bottom), 1)
            pygame.draw.line(surf, (55, 42, 28),    (r.right, r.top),   r.bottomright,  1)
            pygame.draw.line(surf, (55, 42, 28),    (r.left,  r.bottom), r.bottomright,  1)

        # Static labels
        for txt, bx, by in [
            ("AMMO",   12,  52),
            ("HEALTH", 298,  52),
            ("ARMOR",  452,  52),
        ]:
            lbl = self.lbl_font.render(txt, True, _LABEL_COLOR)
            surf.blit(lbl, (bx, by))

        self._bar_surf = surf
        self._panel_rects = panels   # save for dynamic drawing

    def _build_face_sprites(self) -> None:
        """Generate 5 face states (100 % → dead) as tiny pixel portraits."""
        states = [
            # skin,        eye-sclera,   pupil/detail
            ((180, 130, 90), (200, 200, 200), (30,  30,  30)),   # 80-100 % fine
            ((170, 115, 75), (200, 200, 200), (30,  30,  30)),   # 60-80 %
            ((160,  95, 65), (220, 180, 100), (80,  30,  10)),   # 40-60 % worried
            ((140,  70, 50), (220,  80,  30), (60,   0,   0)),   # 20-40 % hurt
            (( 80,  50, 40), ( 60,  20,  10), ( 20,   0,   0)),  # < 20 % critical
        ]
        for skin, sclera, pupil in states:
            s = pygame.Surface((96, 56), pygame.SRCALPHA)
            # head oval
            pygame.draw.ellipse(s, skin, (8, 4, 80, 48))
            # eyes
            for ex in (28, 58):
                pygame.draw.ellipse(s, sclera, (ex - 8, 14, 16, 12))
                pygame.draw.circle(s, pupil,   (ex,     20),  4)
            # mouth — grimace that worsens with damage
            mouth_pts = [(32, 38), (48, 41), (64, 38)]
            pygame.draw.lines(s, (60, 20, 10), False, mouth_pts, 2)
            # cyber detail — small glowing Orx "eye implant"
            pygame.draw.circle(s, (0, 220, 255), (48, 20), 6)
            pygame.draw.circle(s, (0, 100, 180), (48, 20), 3)
            self._face_surfs.append(s)

    def _face_index(self, health: float) -> int:
        pct = health / C.PLAYER_HEALTH_MAX
        if pct > 0.8:  return 0
        if pct > 0.6:  return 1
        if pct > 0.4:  return 2
        if pct > 0.2:  return 3
        return 4

    def _draw_status_bar(self, player: Player, weapon: Weapon) -> None:
        if self._bar_surf is None:
            return
        # Blit the static background
        self.screen.blit(self._bar_surf, (0, self._bar_y))
        y0 = self._bar_y   # absolute screen Y of bar top

        # ---- AMMO panel ----
        ammo_col = _NUMBER_RED if weapon.ammo <= 5 else _NUMBER_GOLD
        self._draw_big_number(weapon.ammo, 20, y0 + 12, ammo_col, width=3)

        # small arms dots (how many mag-refills remain — visual flavour)
        arms_pct = weapon.ammo / C.WEAPON_AMMO_MAX
        dot_x = 20
        for i in range(6):
            col = _NUMBER_GOLD if i < round(arms_pct * 6) else (50, 40, 28)
            pygame.draw.rect(self.screen, col, (dot_x + i * 18, y0 + 52, 14, 8))

        # ---- FACE portrait panel ----
        face_idx  = self._face_index(player.health)
        face_surf = self._face_surfs[face_idx]
        fx = 156 + (130 - face_surf.get_width())  // 2
        fy = y0  + (C.HUD_BAR_HEIGHT - face_surf.get_height()) // 2
        self.screen.blit(face_surf, (fx, fy))

        # ---- HEALTH ----
        hp_pct = player.health / C.PLAYER_HEALTH_MAX
        hp_col  = _NUMBER_RED if hp_pct < 0.25 else (_NUMBER_GOLD if hp_pct < 0.6 else _NUMBER_GREEN)
        self._draw_big_number(int(player.health), 298, y0 + 12, hp_col, width=3)

        # small health bar
        bw, bh = 120, 6
        bx, by = 298, y0 + 46
        pygame.draw.rect(self.screen, (40, 18, 12), (bx, by, bw, bh))
        pygame.draw.rect(self.screen, hp_col, (bx, by, int(bw * hp_pct), bh))

        # ---- ARMOR ----
        armor = getattr(player, "armor", 0)
        armor_max = C.PLAYER_ARMOR_MAX
        arm_pct = min(1.0, armor / armor_max) if armor_max > 0 else 0
        arm_col = (80, 180, 255) if arm_pct > 0 else (50, 50, 50)
        self._draw_big_number(int(armor), 452, y0 + 12, arm_col, width=3)
        bx2 = 452
        pygame.draw.rect(self.screen, (12, 18, 40), (bx2, by, bw, bh))
        pygame.draw.rect(self.screen, arm_col, (bx2, by, int(bw * arm_pct), bh))

        # ---- XP bar (right side) ----
        xp_x, xp_y = 608, y0 + 10
        xp_w, xp_h = 320, 12
        # draw on screen (no player.stats here — use level_xp if available via attribute)
        # We'll hook into player attributes set by game.py (xp_pct, level)
        xp_pct   = getattr(player, "_hud_xp_pct",  0.0)
        level    = getattr(player, "_hud_level",    1)
        level_s  = self.xp_font.render(f"LVL {level}", True, _XP_BAR_COLOR)
        self.screen.blit(level_s, (xp_x, xp_y - 2))
        pygame.draw.rect(self.screen, _XP_BG_COLOR,  (xp_x, xp_y + 16, xp_w, xp_h))
        pygame.draw.rect(self.screen, _XP_BAR_COLOR, (xp_x, xp_y + 16, int(xp_w * xp_pct), xp_h))
        # XP label
        xp_lbl = self.xp_font.render("XP", True, _LABEL_COLOR)
        self.screen.blit(xp_lbl, (xp_x, xp_y + 30))

        # Right edge: level name / stat summary
        stat_x, stat_y = 614, y0 + 48
        stats_txt = (
            f"SPD {getattr(player, '_hud_spd', 1.0):.1f}  "
            f"LGC {getattr(player, '_hud_lgc', 1.0):.1f}  "
            f"HCK {getattr(player, '_hud_hck', 1.0):.1f}"
        )
        s_surf = self.xp_font.render(stats_txt, True, _LABEL_COLOR)
        self.screen.blit(s_surf, (stat_x, stat_y))

    def _draw_big_number(self, value: int, x: int, y: int,
                         color: tuple, width: int = 3) -> None:
        """Draw a large mono-spaced number in DOOM style."""
        txt = str(value).rjust(width)
        rendered = self.num_font.render(txt, True, color)
        self.screen.blit(rendered, (x, y))

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------

    def _draw_minimap(self, player: Player, world: WorldMap,
                      enemies: list[Enemy]) -> None:
        map_x, map_y = 10, 10
        tile   = C.MINIMAP_TILE
        radius = int(C.MINIMAP_SIZE / (2 * tile))

        bg = pygame.Surface((C.MINIMAP_SIZE, C.MINIMAP_SIZE), pygame.SRCALPHA)
        bg.fill(_MINIMAP_BG)
        self.screen.blit(bg, (map_x, map_y))

        px, py = int(player.x), int(player.y)

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                wx, wy = px + dx, py + dy
                if not world.is_wall(wx, wy):
                    continue
                sx = map_x + (dx + radius) * tile
                sy = map_y + (dy + radius) * tile
                t  = world.get_tile(wx, wy)
                colors = {
                    C.WALL_STONE:  (100,  75,  50),
                    C.WALL_METAL:  ( 70,  80,  90),
                    C.WALL_DOOR:   (130,  80,  40),
                    C.WALL_SECRET: ( 90,  75,  60),
                }
                pygame.draw.rect(self.screen, colors.get(t, (90, 70, 50)),
                                 (sx, sy, tile, tile))

        for enemy in enemies:
            if not enemy.is_alive:
                continue
            edx = int(enemy.x) - px
            edy = int(enemy.y) - py
            if abs(edx) > radius or abs(edy) > radius:
                continue
            sx = map_x + (edx + radius) * tile + tile // 2
            sy = map_y + (edy + radius) * tile + tile // 2
            pygame.draw.circle(self.screen, (220, 40, 20), (sx, sy), 2)

        pmx = map_x + radius * tile + tile // 2
        pmy = map_y + radius * tile + tile // 2
        pygame.draw.circle(self.screen, (0, 220, 255), (pmx, pmy), 3)
        dx = math.cos(player.angle) * tile * 2
        dy = math.sin(player.angle) * tile * 2
        pygame.draw.line(self.screen, (0, 220, 255),
                         (pmx, pmy), (int(pmx + dx), int(pmy + dy)), 2)

        # Border
        pygame.draw.rect(self.screen, _BAR_BORDER,
                         (map_x, map_y, C.MINIMAP_SIZE, C.MINIMAP_SIZE), 1)

    # ------------------------------------------------------------------
    # Centre messages
    # ------------------------------------------------------------------

    def _draw_messages(self) -> None:
        y = self._bar_y // 3
        for text, time_left in self.messages:
            alpha = min(255, int(time_left * 100))
            surf  = self.msg_font.render(text, True, _MSG_COLOR)
            # Dark shadow
            shadow = self.msg_font.render(text, True, (20, 10, 5))
            shadow.set_alpha(min(255, alpha))
            surf.set_alpha(min(255, alpha))
            tx = (C.SCREEN_WIDTH - surf.get_width()) // 2
            self.screen.blit(shadow, (tx + 2, y + 2))
            self.screen.blit(surf,   (tx, y))
            y -= 38

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def _draw_debug(self, player: Player) -> None:
        lines = [
            f"FPS: {self.fps}",
            f"POS: ({player.x:.1f}, {player.y:.1f})",
            f"ANGLE: {math.degrees(player.angle):.0f}°",
        ]
        y = C.MINIMAP_SIZE + 20
        for line in lines:
            surf = self.small_font.render(line, True, (255, 255, 0))
            self.screen.blit(surf, (10, y))
            y += 20
