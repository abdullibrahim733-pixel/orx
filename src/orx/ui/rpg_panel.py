"""RPG stat panel overlay — DOOM-terminal aesthetic."""

from __future__ import annotations

import pygame
from orx.rpg.stats import PlayerStats


_PANEL_BG     = (12,  10,   8, 210)
_BORDER_COLOR = (130,  85,  40)
_TITLE_COLOR  = (220,  50,  10)
_VALUE_COLOR  = (215, 180,  60)
_DIM_COLOR    = (130, 100,  60)
_AVAIL_COLOR  = ( 60, 220, 255)
_BAR_FILL     = (180,  50,  10)
_BAR_BG       = ( 40,  20,  10)
_BAR_XP_FILL  = ( 60, 180, 255)
_BAR_XP_BG    = ( 10,  20,  50)


def _doom_font(size: int) -> pygame.font.Font:
    for name in ("DejaVu Sans Mono", "Courier New", "monospace"):
        try:
            f = pygame.font.SysFont(name, size, bold=True)
            if f:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, size)


class RPGPanel:
    """Full-screen stat overlay — shown when TAB is held."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font       = _doom_font(28)
        self.small_font = _doom_font(20)
        self.title_font = _doom_font(34)
        self.visible    = False

        W, H = screen.get_width(), screen.get_height()
        panel_w, panel_h = 360, 390
        self._rect = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2,
                                  panel_w, panel_h)

    def render(self, stats: PlayerStats) -> None:
        if not self.visible:
            return

        # Semi-transparent background
        bg = pygame.Surface(self._rect.size, pygame.SRCALPHA)
        bg.fill(_PANEL_BG)
        self.screen.blit(bg, self._rect.topleft)

        # Double border — outer dark, inner gold
        pygame.draw.rect(self.screen, (40, 25, 12), self._rect, 4)
        inner = self._rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, _BORDER_COLOR, inner, 2)

        x = self._rect.x + 20
        y = self._rect.y + 18

        # Title
        title = self.title_font.render("/// ORX SYS-STATS ///", True, _TITLE_COLOR)
        self.screen.blit(title, (x, y))
        y += 38

        # Separator line
        pygame.draw.line(self.screen, _BORDER_COLOR,
                         (x, y), (self._rect.right - 20, y), 1)
        y += 10

        # Level + XP
        self._row(f"LEVEL  {stats.level:>2}", x, y, _VALUE_COLOR)
        y += 28

        xp_pct = stats.xp / max(1, stats.xp_to_next)
        self._bar(x, y, 300, 10, xp_pct, _BAR_XP_FILL, _BAR_XP_BG)
        xp_label = self.small_font.render(
            f"XP  {stats.xp}/{stats.xp_to_next}", True, _DIM_COLOR)
        self.screen.blit(xp_label, (x, y + 14))
        y += 38

        # Separator
        pygame.draw.line(self.screen, _BORDER_COLOR,
                         (x, y), (self._rect.right - 20, y), 1)
        y += 10

        # Stat points available
        sp_col = _AVAIL_COLOR if stats.stat_points > 0 else _DIM_COLOR
        self._row(f"STAT PTS  {stats.stat_points:>2}", x, y, sp_col)
        y += 32

        # Stats with bars
        for label, value, key, max_v in [
            ("SPEED      [Q]", stats.speed,   "speed",   8.0),
            ("LOGIC-CORE [W]", stats.logic,   "logic",   8.0),
            ("HACKING    [E]", stats.hacking, "hacking", 8.0),
        ]:
            pct = (value - 1.0) / (max_v - 1.0)
            self._row(f"{label}  {value:.1f}", x, y, _VALUE_COLOR)
            y += 22
            self._bar(x + 10, y, 280, 8, max(0.0, pct), _BAR_FILL, _BAR_BG)
            y += 18

        # Separator
        y += 4
        pygame.draw.line(self.screen, _BORDER_COLOR,
                         (x, y), (self._rect.right - 20, y), 1)
        y += 10

        # Derived multipliers
        dmg_mult = 1.0 + (stats.logic   - 1.0) * 0.5
        spd_mult = stats.speed
        xp_bonus = (stats.hacking - 1.0) * 20.0
        for label, val, unit in [
            ("DMG MULT",  dmg_mult,  "x"),
            ("SPD MULT",  spd_mult,  "x"),
            ("XP BONUS",  xp_bonus,  "%"),
        ]:
            self._row(f"{label}  {val:+.1f}{unit}", x, y, _DIM_COLOR)
            y += 24

    def _row(self, text: str, x: int, y: int, color: tuple) -> None:
        surf = self.small_font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _bar(self, x: int, y: int, w: int, h: int,
             pct: float, fill: tuple, bg: tuple) -> None:
        pygame.draw.rect(self.screen, bg,   (x, y, w, h))
        pygame.draw.rect(self.screen, fill, (x, y, int(w * pct), h))
        pygame.draw.rect(self.screen, _BORDER_COLOR, (x, y, w, h), 1)
