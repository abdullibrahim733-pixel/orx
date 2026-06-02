"""CRT post-processing — DOOM-style heavy vignette + scanlines."""

from __future__ import annotations

import math
import pygame
from orx import constants as C


class PostProcess:
    """Applies CRT-style post-processing to the 3D viewport only (above HUD bar)."""

    def __init__(self, screen: pygame.Surface):
        self.screen    = screen
        self.enabled   = True
        self.intensity = 0.45   # slightly heavier vignette than before
        self._scanlines: pygame.Surface | None = None
        self._vignette:  pygame.Surface | None = None
        self._generate_overlays()

    def _generate_overlays(self) -> None:
        view_h = C.SCREEN_HEIGHT - C.HUD_BAR_HEIGHT

        # Scanlines — every other pixel-row gets a faint darkening
        scanlines = pygame.Surface((C.SCREEN_WIDTH, view_h), pygame.SRCALPHA)
        for y in range(0, view_h, 2):
            pygame.draw.line(scanlines, (0, 0, 0, 50),
                             (0, y), (C.SCREEN_WIDTH, y))
        self._scanlines = scanlines

        # Vignette — radial darkness toward edges of the 3D viewport
        vignette = pygame.Surface((C.SCREEN_WIDTH, view_h), pygame.SRCALPHA)
        cx  = C.SCREEN_WIDTH / 2
        cy  = view_h / 2
        max_dist = math.hypot(cx, cy)
        for y in range(view_h):
            for x in range(C.SCREEN_WIDTH):
                dist     = math.hypot(x - cx, y - cy)
                darkness = min(1.0, (dist / max_dist) ** 1.6) * self.intensity
                alpha    = int(darkness * 200)
                vignette.set_at((x, y), (0, 0, 0, alpha))
        self._vignette = vignette

    def apply(self) -> None:
        if not self.enabled:
            return
        # Apply only to the 3D viewport area
        if self._scanlines:
            self.screen.blit(self._scanlines, (0, 0))
        if self._vignette:
            self.screen.blit(self._vignette, (0, 0))
