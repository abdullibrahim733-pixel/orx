"""Rendering pipeline for walls, floor, ceiling — DOOM/Orx aesthetic."""

from __future__ import annotations

import pygame
from orx import constants as C
from orx.engine.raycaster import RayHit
from orx.assets.procedural import ProceduralAssets


class Renderer:
    """Renders raycast results to screen."""

    def __init__(self, screen: pygame.Surface, assets: ProceduralAssets):
        self.screen = screen
        self.assets = assets
        self._precompute_gradients()

    def _precompute_gradients(self) -> None:
        # Only render gradients for the 3D view area (above the HUD bar)
        view_h = C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT
        half   = view_h // 2

        sky = pygame.Surface((C.SCREEN_WIDTH, half))
        for y in range(half):
            t = y / half
            r = int(C.COLOR_SKY_TOP[0] + (C.COLOR_SKY_BOTTOM[0] - C.COLOR_SKY_TOP[0]) * t)
            g = int(C.COLOR_SKY_TOP[1] + (C.COLOR_SKY_BOTTOM[1] - C.COLOR_SKY_TOP[1]) * t)
            b = int(C.COLOR_SKY_TOP[2] + (C.COLOR_SKY_BOTTOM[2] - C.COLOR_SKY_TOP[2]) * t)
            pygame.draw.line(sky, (r, g, b), (0, y), (C.SCREEN_WIDTH, y))
        self._sky_surface  = sky

        floor = pygame.Surface((C.SCREEN_WIDTH, half))
        for y in range(half):
            t = y / half
            r = int(C.COLOR_FLOOR_TOP[0] + (C.COLOR_FLOOR_BOTTOM[0] - C.COLOR_FLOOR_TOP[0]) * t)
            g = int(C.COLOR_FLOOR_TOP[1] + (C.COLOR_FLOOR_BOTTOM[1] - C.COLOR_FLOOR_TOP[1]) * t)
            b = int(C.COLOR_FLOOR_TOP[2] + (C.COLOR_FLOOR_BOTTOM[2] - C.COLOR_FLOOR_TOP[2]) * t)
            pygame.draw.line(floor, (r, g, b), (0, y), (C.SCREEN_WIDTH, y))
        self._floor_surface = floor

        self._view_h = view_h
        self._half   = half

    def render(self, hits: list[RayHit], z_buffer: list[float]) -> None:
        view_h = self._view_h
        half   = self._half

        # Sky and floor fill the 3D viewport (above the HUD bar)
        self.screen.blit(self._sky_surface,   (0, 0))
        self.screen.blit(self._floor_surface, (0, half))

        wall_tex = self.assets.wall_textures

        for col, hit in enumerate(hits):
            if hit.wall_type == 0 or hit.distance >= C.MAX_DEPTH:
                z_buffer[col] = C.MAX_DEPTH
                continue

            perp_dist   = hit.distance
            line_height = int(view_h / perp_dist)
            draw_start  = int(half - line_height / 2)
            draw_end    = int(half + line_height / 2)

            if draw_start < 0:
                draw_start = 0
            if draw_end >= view_h:
                draw_end = view_h - 1

            # Distance shading (DOOM doesn't do linear fog exactly, but this is close)
            shade = max(0.10, min(1.0, 1.0 - (perp_dist / C.MAX_DEPTH) ** 0.8))
            # DOOM darkens side-hit walls (EW vs NS)
            if hit.side == 1:
                shade *= 0.65

            col_height = draw_end - draw_start + 1
            if col_height <= 0:
                z_buffer[col] = perp_dist
                continue

            screen_x = col * C.STRIP_WIDTH

            tex_key = hit.wall_type
            if tex_key in wall_tex:
                tex   = wall_tex[tex_key]
                tex_w = tex.get_width()
                tex_x = int(hit.tex_x * tex_w) % tex_w
                try:
                    tex_col = tex.subsurface((tex_x, 0, 1, tex.get_height()))
                    scaled  = pygame.transform.scale(tex_col, (C.STRIP_WIDTH, col_height))
                    shade_v = int(shade * 255)
                    scaled.fill((shade_v, shade_v, shade_v), None, pygame.BLEND_RGB_MULT)
                    self.screen.blit(scaled, (screen_x, draw_start))
                except Exception:
                    base = self._wall_color(hit.wall_type)
                    pygame.draw.rect(self.screen,
                                     tuple(int(c * shade) for c in base),
                                     (screen_x, draw_start, C.STRIP_WIDTH, col_height))
            else:
                base = self._wall_color(hit.wall_type)
                pygame.draw.rect(self.screen,
                                 tuple(int(c * shade) for c in base),
                                 (screen_x, draw_start, C.STRIP_WIDTH, col_height))

            z_buffer[col] = perp_dist

    @staticmethod
    def _wall_color(wall_type: int) -> tuple[int, int, int]:
        # DOOM brownstone palette fallbacks
        colors = {
            C.WALL_STONE:  (120, 82, 48),
            C.WALL_METAL:  ( 72, 80, 95),
            C.WALL_DOOR:   (100, 65, 38),
            C.WALL_SECRET: (110, 78, 50),
        }
        return colors.get(wall_type, (100, 70, 45))
