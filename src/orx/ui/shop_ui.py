"""The System Store holographic terminal — fullscreen overlay with scan-line effect."""

from __future__ import annotations

import pygame
from orx import constants as C


_TIER_COLORS = {
    "E-Rank": (160, 120, 60),
    "C-Rank": (160, 160, 200),
    "A-Rank": (255, 200, 50),
    "S-Rank": (255, 50, 50),
}


class ShopUI:
    """Full-screen holo-terminal overlay for The System Store."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.visible = False
        self.open_timer = 0.0
        self.selected_idx = 0
        self.scroll_offset = 0
        self.notification_text = ""
        self.notification_timer = 0.0
        self.error_text = ""
        self.error_timer = 0.0

        self.font_title = pygame.font.SysFont("DejaVu Sans Mono", 34, bold=True)
        self.font_item = pygame.font.SysFont("DejaVu Sans Mono", 20, bold=True)
        self.font_detail = pygame.font.SysFont("DejaVu Sans Mono", 16)
        self.font_gold = pygame.font.SysFont("DejaVu Sans Mono", 26, bold=True)
        self.font_notify = pygame.font.SysFont("DejaVu Sans Mono", 22, bold=True)

        self._scanline_surf = None
        self._build_scanlines()

    def _build_scanlines(self) -> None:
        w, h = C.SCREEN_WIDTH, C.SCREEN_HEIGHT
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 3):
            pygame.draw.line(s, (0, 0, 0, 60), (0, y), (w, y))
        self._scanline_surf = s

    def open(self) -> None:
        self.visible = True
        self.open_timer = 0.0
        self.selected_idx = 0
        self.scroll_offset = 0

    def close(self) -> None:
        self.visible = False
        self.notification_text = ""
        self.error_text = ""

    def show_notification(self, text: str, is_error: bool = False) -> None:
        if is_error:
            self.error_text = text
            self.error_timer = 3.0
        else:
            self.notification_text = text
            self.notification_timer = 3.0

    def handle_input(self, event: pygame.event.Event, items: list[dict]) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                    self._clamp_scroll()
                return True
            elif event.key == pygame.K_DOWN:
                if self.selected_idx < len(items) - 1:
                    self.selected_idx += 1
                    self._clamp_scroll()
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if items:
                    return True  # signal "buy selected item"
            elif event.key == pygame.K_s:
                self.close()
                return True

        return False

    def _clamp_scroll(self) -> None:
        max_visible = 8
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_idx - max_visible + 1

    def render(self, items: list[dict], player_gold: int, player_level: int,
               stats) -> None:
        if not self.visible:
            return

        self.open_timer += 1 / 60.0
        alpha = min(255, int(self.open_timer * 510))

        if self.notification_timer > 0:
            self.notification_timer -= 1 / 60.0
        if self.error_timer > 0:
            self.error_timer -= 1 / 60.0

        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        overlay.fill((6, 8, 14))
        overlay.set_alpha(min(240, alpha))
        self.screen.blit(overlay, (0, 0))

        for bx in range(3):
            c = tuple(int(cv * (1 - bx / 3)) for cv in (60, 140, 220))
            pygame.draw.rect(self.screen, c,
                             (bx, bx, C.SCREEN_WIDTH - bx * 2,
                              C.SCREEN_HEIGHT - bx * 2), 1)

        line_pos = (self.open_timer * 120) % C.SCREEN_HEIGHT
        for line_idx in range(-20, 20):
            ly = line_pos + line_idx * 40
            if 0 <= ly < C.SCREEN_HEIGHT:
                la = max(0, 60 - abs(line_idx) * 8)
                pygame.draw.line(self.screen, (80, 180, 255, la),
                                 (0, ly), (C.SCREEN_WIDTH, ly), 1)

        title = self.font_title.render("/// THE SYSTEM STORE ///", True, (60, 180, 255))
        tx = (C.SCREEN_WIDTH - title.get_width()) // 2
        self.screen.blit(title, (tx, 18))
        pygame.draw.line(self.screen, (40, 80, 160),
                         (60, 56), (C.SCREEN_WIDTH - 60, 56), 1)

        gold_text = self.font_gold.render(f"{player_gold} G", True, (255, 210, 40))
        self.screen.blit(gold_text, (C.SCREEN_WIDTH - 180, 22))

        lvl_text = self.font_detail.render(f"Lv.{player_level}", True, (120, 180, 220))
        self.screen.blit(lvl_text, (C.SCREEN_WIDTH - 180, 52))

        hint = self.font_detail.render(
            "UP/DOWN select  |  SPACE buy  |  S close", True, (80, 100, 140))
        hx = (C.SCREEN_WIDTH - hint.get_width()) // 2
        self.screen.blit(hint, (hx, C.SCREEN_HEIGHT - 28))

        self._render_item_list(items, player_level, player_gold)

        if self.notification_text and self.notification_timer > 0:
            na = min(255, int(self.notification_timer * 120))
            notif = self.font_notify.render(self.notification_text, True,
                                            (100, 255, 100))
            notif.set_alpha(na)
            nx = (C.SCREEN_WIDTH - notif.get_width()) // 2
            self.screen.blit(notif, (nx, C.SCREEN_HEIGHT // 2 + 140))

        if self.error_text and self.error_timer > 0:
            ea = min(255, int(self.error_timer * 120))
            err = self.font_notify.render(self.error_text, True, (255, 80, 80))
            err.set_alpha(ea)
            ex = (C.SCREEN_WIDTH - err.get_width()) // 2
            self.screen.blit(err, (ex, C.SCREEN_HEIGHT // 2 + 140))

        self.screen.blit(self._scanline_surf, (0, 0))

    def _render_item_list(self, items: list[dict], player_level: int, player_gold: int) -> None:
        start_y = 70
        row_h = 46
        max_visible = 8
        vis_items = items[self.scroll_offset:self.scroll_offset + max_visible]
        pad_x = 60

        for i, item in enumerate(vis_items):
            actual_idx = self.scroll_offset + i
            y = start_y + i * row_h
            is_selected = actual_idx == self.selected_idx

            if is_selected:
                sel = pygame.Surface((C.SCREEN_WIDTH - pad_x * 2, row_h - 2))
                sel.fill((20, 40, 80, 100))
                sel.set_alpha(100)
                self.screen.blit(sel, (pad_x, y))

            tier_col = _TIER_COLORS.get(item["tier"], (180, 180, 180))
            name = item["name"]
            if item.get("is_daily_deal"):
                name += " ★"

            name_color = (220, 220, 230)
            name_surf = self.font_item.render(name, True, name_color)
            self.screen.blit(name_surf, (pad_x + 8, y + 4))

            cost = item["purchase_cost"]
            can_afford = player_gold >= cost
            cost_col = (255, 210, 40) if can_afford else (180, 60, 60)
            cost_surf = self.font_detail.render(f"{cost}G", True, cost_col)
            self.screen.blit(cost_surf, (C.SCREEN_WIDTH - pad_x - 100, y + 4))

            stock = item.get("available_stock", 0)
            stock_color = (100, 200, 100) if stock > 0 else (100, 60, 60)
            stock_surf = self.font_detail.render(f"x{stock}", True, stock_color)
            self.screen.blit(stock_surf, (C.SCREEN_WIDTH - pad_x - 50, y + 4))

            tier_surf = self.font_detail.render(item["tier"], True, tier_col)
            self.screen.blit(tier_surf, (pad_x + 280, y + 4))

            req = item["required_level"]
            req_ok = player_level >= req
            req_col = (100, 200, 100) if req_ok else (200, 80, 80)
            req_surf = self.font_detail.render(f"Lv.{req}", True, req_col)
            self.screen.blit(req_surf, (pad_x + 370, y + 4))

            mods = item.get("modifiers", {})
            mod_text = "  ".join(
                f"+{v} {k.replace('_', ' ')}" for k, v
                in sorted(mods.items()) if v > 0
            )
            if mod_text:
                mod_surf = self.font_detail.render(mod_text, True, (140, 160, 180))
                self.screen.blit(mod_surf, (pad_x + 8, y + 22))

            if is_selected:
                cat_surf = self.font_detail.render(
                    f"[{item.get('category', '?').title()}]", True, (100, 140, 180))
                self.screen.blit(cat_surf,
                                 (C.SCREEN_WIDTH - pad_x - 140, y + 22))

            if item.get("is_daily_deal") and is_selected:
                star_surf = self.font_detail.render("DAILY DEAL", True,
                                                    (255, 200, 50))
                self.screen.blit(star_surf,
                                 (C.SCREEN_WIDTH - pad_x - 140, y + 24))
