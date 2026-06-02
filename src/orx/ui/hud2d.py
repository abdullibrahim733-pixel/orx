"""2D mode HUD — overlay with stats, minimap, and competitive tracking."""

from __future__ import annotations

import math
import pygame
from orx import constants as C
from orx.rpg.stats import PlayerStats


class HUD2D:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_big = pygame.font.SysFont("DejaVu Sans Mono", 28, bold=True)
        self.font_small = pygame.font.SysFont("DejaVu Sans Mono", 18, bold=True)
        self.font_tiny = pygame.font.SysFont("DejaVu Sans Mono", 14)
        self.messages: list[tuple[str, float]] = []
        self.fps = 0
        self.show_debug = False

    def add_message(self, text: str) -> None:
        self.messages.append((text, 3.0))

    def update_messages(self, dt: float) -> None:
        self.messages = [(t, time - dt) for t, time in self.messages if time - dt > 0]

    def render(self, player, stats: PlayerStats, enemies: list,
               boss, kills: int, level: int, grid: list) -> None:
        self._draw_stat_overlay(player, stats, kills, level, boss)
        self._draw_minimap(player, enemies, boss, grid)
        self._draw_messages()
        self._draw_crosshair()
        if self.show_debug:
            self._draw_debug(player)

    def _draw_stat_overlay(self, player, stats, kills, level, boss) -> None:
        bar_y = C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT

        bg = pygame.Surface((C.SCREEN_WIDTH, C.HUD_BAR_HEIGHT))
        bg.fill((12, 10, 8))
        self.screen.blit(bg, (0, bar_y))
        pygame.draw.line(self.screen, (60, 45, 30), (0, bar_y), (C.SCREEN_WIDTH, bar_y), 2)

        hp_pct = player.health / max(1, player.max_health)
        hp_col = (220, 30, 10) if hp_pct < 0.3 else (60, 210, 60)
        hp_text = self.font_big.render(f"HP {int(player.health):>3}", True, hp_col)
        self.screen.blit(hp_text, (12, bar_y + 8))
        pygame.draw.rect(self.screen, (40, 10, 10), (12, bar_y + 40, 140, 12))
        pygame.draw.rect(self.screen, hp_col, (12, bar_y + 40, int(140 * hp_pct), 12))
        pygame.draw.rect(self.screen, (80, 60, 40), (12, bar_y + 40, 140, 12), 1)

        level_text = self.font_big.render(f"LVL {stats.level:>2}", True, (80, 180, 255))
        self.screen.blit(level_text, (C.SCREEN_WIDTH // 2 - 60, bar_y + 8))
        xp_pct = stats.xp / max(1, stats.xp_to_next)
        xp_w = 180
        pygame.draw.rect(self.screen, (10, 20, 50), (C.SCREEN_WIDTH // 2 - 90, bar_y + 40, xp_w, 12))
        pygame.draw.rect(self.screen, (60, 180, 255), (C.SCREEN_WIDTH // 2 - 90, bar_y + 40, int(xp_w * xp_pct), 12))
        pygame.draw.rect(self.screen, (80, 60, 40), (C.SCREEN_WIDTH // 2 - 90, bar_y + 40, xp_w, 12), 1)

        kills_text = self.font_small.render(f"KILLS {kills}", True, (200, 180, 100))
        self.screen.blit(kills_text, (C.SCREEN_WIDTH - 260, bar_y + 8))
        gold_text = self.font_small.render(f"GOLD {stats.gold}", True, (255, 210, 40))
        self.screen.blit(gold_text, (C.SCREEN_WIDTH - 260, bar_y + 28))
        lvl_text = self.font_small.render(f"FLOOR {level}/{C.MAX_LEVELS_2D}", True, (150, 150, 150))
        self.screen.blit(lvl_text, (C.SCREEN_WIDTH - 260, bar_y + 48))

        sp = getattr(stats, 'stat_points', 0)
        if sp > 0:
            sp_text = self.font_small.render(f"STAT PTS: {sp} (TAB)", True, (60, 220, 255))
            self.screen.blit(sp_text, (C.SCREEN_WIDTH - 260, bar_y + 52))

        if boss is not None and boss.is_alive:
            boss_text = self.font_small.render(f"BOSS: {boss.name}", True, (255, 100, 50))
            self.screen.blit(boss_text, (C.SCREEN_WIDTH // 2 + 100, bar_y + 10))
            bp_pct = boss.health / max(1, boss.max_health)
            bw = 150
            pygame.draw.rect(self.screen, (40, 10, 10), (C.SCREEN_WIDTH // 2 + 100, bar_y + 32, bw, 10))
            pygame.draw.rect(self.screen, (255, 50, 0), (C.SCREEN_WIDTH // 2 + 100, bar_y + 32, int(bw * bp_pct), 10))
            pygame.draw.rect(self.screen, (100, 60, 40), (C.SCREEN_WIDTH // 2 + 100, bar_y + 32, bw, 10), 1)

    def _draw_minimap(self, player, enemies, boss, grid) -> None:
        map_size = 100
        tile = 4
        map_x, map_y = C.SCREEN_WIDTH - map_size - 10, 10
        cx, cy = map_size // 2, map_size // 2

        bg = pygame.Surface((map_size, map_size), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg, (map_x, map_y))
        pygame.draw.rect(self.screen, (60, 45, 30), (map_x, map_y, map_size, map_size), 1)

        if not grid:
            return

        px, py = int(player.x), int(player.y)
        h = len(grid)
        w = len(grid[0]) if h else 0
        for dy in range(-cx // tile, cx // tile + 1):
            for dx in range(-cx // tile, cx // tile + 1):
                wx, wy = px + dx, py + dy
                if wy < 0 or wy >= h or wx < 0 or wx >= w:
                    continue
                if grid[wy][wx] == 0:
                    continue
                sx = map_x + cx + dx * tile
                sy = map_y + cy + dy * tile
                pygame.draw.rect(self.screen, (60, 50, 35), (sx, sy, tile, tile))

        for enemy in enemies:
            if not enemy.is_alive:
                continue
            edx = int(enemy.x) - px
            edy = int(enemy.y) - py
            if abs(edx) > cx // tile or abs(edy) > cy // tile:
                continue
            sx = map_x + cx + edx * tile
            sy = map_y + cy + edy * tile
            pygame.draw.circle(self.screen, (220, 40, 20), (sx, sy), 2)

        if boss is not None and boss.is_alive:
            edx = int(boss.x) - px
            edy = int(boss.y) - py
            if abs(edx) <= cx // tile and abs(edy) <= cy // tile:
                sx = map_x + cx + edx * tile
                sy = map_y + cy + edy * tile
                pygame.draw.circle(self.screen, (255, 200, 0), (sx, sy), 3)
                pygame.draw.circle(self.screen, (255, 50, 0), (sx, sy), 2)

        pmx = map_x + cx
        pmy = map_y + cy
        pygame.draw.circle(self.screen, (0, 220, 255), (pmx, pmy), 3)
        dx = math.cos(player.angle) * 6
        dy = math.sin(player.angle) * 6
        pygame.draw.line(self.screen, (0, 220, 255), (pmx, pmy),
                         (int(pmx + dx), int(pmy + dy)), 2)

    def _draw_crosshair(self) -> None:
        cx, cy = C.SCREEN_WIDTH // 2, (C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT) // 2
        gap, arm = 4, 8
        col = (180, 180, 180)
        pygame.draw.line(self.screen, col, (cx - gap - arm, cy), (cx - gap, cy), 2)
        pygame.draw.line(self.screen, col, (cx + gap, cy), (cx + gap + arm, cy), 2)
        pygame.draw.line(self.screen, col, (cx, cy - gap - arm), (cx, cy - gap), 2)
        pygame.draw.line(self.screen, col, (cx, cy + gap), (cx, cy + gap + arm), 2)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 2)

    def _draw_messages(self) -> None:
        y = 60
        for text, time_left in self.messages:
            alpha = min(255, int(time_left * 100))
            surf = self.font_big.render(text, True, (255, 200, 50))
            shadow = self.font_big.render(text, True, (20, 10, 5))
            shadow.set_alpha(min(255, alpha))
            surf.set_alpha(min(255, alpha))
            tx = (C.SCREEN_WIDTH - surf.get_width()) // 2
            self.screen.blit(shadow, (tx + 2, y + 2))
            self.screen.blit(surf, (tx, y))
            y -= 34

    def _draw_debug(self, player) -> None:
        lines = [
            f"FPS: {self.fps}",
            f"POS: ({player.x:.1f}, {player.y:.1f})",
            f"ANGLE: {math.degrees(player.angle):.0f}°",
        ]
        y = 10
        for line in lines:
            surf = self.font_tiny.render(line, True, (255, 255, 0))
            self.screen.blit(surf, (10, y))
            y += 16
