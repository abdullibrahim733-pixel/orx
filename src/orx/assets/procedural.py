"""Procedurally generated textures, sprites, and effects — DOOM/Orx hybrid."""

from __future__ import annotations

import random
import pygame
from orx import constants as C


class ProceduralAssets:
    """Generates all game assets at runtime."""

    def __init__(self):
        self.wall_textures: dict[int, pygame.Surface] = {}
        self.enemy_surfaces: dict[str, pygame.Surface] = {}
        self.weapon_surface: pygame.Surface | None = None
        self.muzzle_flash_surface: pygame.Surface | None = None
        self._generate_wall_textures()
        self._generate_enemy_sprites()
        self._generate_weapon()

    # ------------------------------------------------------------------
    # Wall textures — DOOM brownstone palette
    # ------------------------------------------------------------------

    def _generate_wall_textures(self) -> None:
        tex = 64

        # --- WALL 1: DOOM brownstone brick ---
        stone = pygame.Surface((tex, tex))
        for y in range(tex):
            for x in range(tex):
                # Brick row offset
                row     = y // 12
                col_off = 16 if row % 2 else 0
                in_grout_h = (y % 12) < 2
                in_grout_v = ((x + col_off) % 20) < 2
                if in_grout_h or in_grout_v:
                    # Grout line — near-black brown
                    r = random.randint(28, 38)
                    g = random.randint(20, 28)
                    b = random.randint(12, 18)
                else:
                    # Brick face — warm brown with noise
                    base = random.randint(95, 145)
                    r = min(255, max(0, base + random.randint(-10, 10)))
                    g = min(255, max(0, int(base * 0.70) + random.randint(-8, 8)))
                    b = min(255, max(0, int(base * 0.45) + random.randint(-6, 6)))
                stone.set_at((x, y), (r, g, b))
        self.wall_textures[C.WALL_STONE] = stone

        # --- WALL 2: Dark metal panels (Orx tech) ---
        metal = pygame.Surface((tex, tex))
        for y in range(tex):
            for x in range(tex):
                base = 75
                is_seam = (x % 32 < 2) or (y % 32 < 2)
                is_rivet = ((x % 32 in (4, 27)) and (y % 32 in (4, 27)))
                scratch = random.randint(-6, 6)
                if is_seam:
                    val = 30 + scratch
                elif is_rivet:
                    val = 140
                else:
                    val = base + scratch
                r = min(255, max(0, val))
                g = min(255, max(0, int(val * 0.85)))
                b = min(255, max(0, int(val * 1.1)))
                metal.set_at((x, y), (r, g, b))
        self.wall_textures[C.WALL_METAL] = metal

        # --- WALL 3: DOOM-style door (darker wood-brown frame) ---
        door = pygame.Surface((tex, tex))
        for y in range(tex):
            for x in range(tex):
                # Outer frame vs inner panel
                on_frame = x < 4 or x > 59 or y < 4 or y > 59
                inner    = 14 < x < 50 and 14 < y < 50
                on_handle= 46 < x < 54 and 28 < y < 36
                base     = 55 if on_frame else (75 if inner else 65)
                noise    = random.randint(-8, 8)
                r = min(255, max(0, base + noise + (60 if on_handle else 0)))
                g = min(255, max(0, int((base + noise) * 0.55)))
                b = min(255, max(0, int((base + noise) * 0.30)))
                door.set_at((x, y), (r, g, b))
        self.wall_textures[C.WALL_DOOR] = door

        # --- WALL 4: Secret wall — barely different stone ---
        secret = pygame.Surface((tex, tex))
        for y in range(tex):
            for x in range(tex):
                base  = 108
                noise = random.randint(-10, 10)
                # subtle diagonal crack
                crack = -30 if abs((x - y) % 20) < 1 else 0
                r = min(255, max(0, base + noise + crack))
                g = min(255, max(0, int((base + noise + crack) * 0.72)))
                b = min(255, max(0, int((base + noise + crack) * 0.50)))
                secret.set_at((x, y), (r, g, b))
        self.wall_textures[C.WALL_SECRET] = secret

    # ------------------------------------------------------------------
    # Enemy sprites — hellish Orx cyber-demons
    # ------------------------------------------------------------------

    def _generate_enemy_sprites(self) -> None:
        for etype, stats in C.ENEMY_TYPES.items():
            size = 128  # Increased resolution for character detail
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            cx, cy = size // 2, size // 2
            
            # Colors from reference image
            skin_color     = (175, 155, 45)  # Olive/Ocher goblin skin
            armor_red      = (170, 35, 25)   # Red plate armor
            helmet_blue    = (55, 75, 95)    # Steel/Blue helmet
            clothing_brown = (75, 55, 40)    # Leather/Brown elements
            sword_metal    = (145, 150, 155) # Silver scimitar
            eye_yellow     = (255, 240, 60)  # Feral yellow eyes

            # --- COMMON ORX BODY (The base goblin) ---
            # Legs (simple bipedal stance)
            for lx in [-12, 12]:
                pygame.draw.rect(surf, skin_color, (cx + lx - 4, cy + 15, 8, 20))
                pygame.draw.rect(surf, armor_red,  (cx + lx - 5, cy + 30, 10, 6)) # Foot wraps
            
            # Torso
            pygame.draw.ellipse(surf, skin_color, (cx - 18, cy - 15, 36, 45))
            
            # Head
            head_y = cy - 40
            pygame.draw.ellipse(surf, skin_color, (cx - 20, head_y, 40, 34))
            # Pointy ears
            pygame.draw.polygon(surf, skin_color, [(cx - 18, head_y + 12), (cx - 36, head_y - 8), (cx - 18, head_y + 24)])
            pygame.draw.polygon(surf, skin_color, [(cx + 18, head_y + 12), (cx + 36, head_y - 8), (cx + 18, head_y + 24)])
            # Face details
            pygame.draw.circle(surf, eye_yellow, (cx - 8, head_y + 14), 4)
            pygame.draw.circle(surf, eye_yellow, (cx + 8, head_y + 14), 4)
            pygame.draw.arc(surf, (30, 20, 10), (cx - 12, head_y + 18, 24, 12), 3.14, 0, 2) # Grin

            # --- TYPE-SPECIFIC ARMOR & WEAPONS ---
            if etype == "drone":
                # Light scout helmet
                pygame.draw.arc(surf, helmet_blue, (cx - 21, head_y - 6, 42, 28), 0, 3.14, 16)
                pygame.draw.line(surf, helmet_blue, (cx, head_y - 6), (cx, head_y - 18), 3)
                # Small dagger
                pygame.draw.line(surf, sword_metal, (cx + 18, cy + 10), (cx + 30, cy + 25), 5)

            elif etype == "guard":
                # Spiky helmet & Shoulder pad
                pygame.draw.arc(surf, helmet_blue, (cx - 21, head_y - 6, 42, 28), 0, 3.14, 18)
                pygame.draw.polygon(surf, helmet_blue, [(cx, head_y - 20), (cx - 6, head_y - 4), (cx + 6, head_y - 4)])
                pygame.draw.polygon(surf, helmet_blue, [(cx - 15, head_y - 12), (cx - 20, head_y - 2), (cx - 10, head_y - 2)])
                pygame.draw.polygon(surf, helmet_blue, [(cx + 15, head_y - 12), (cx + 20, head_y - 2), (cx + 10, head_y - 2)])
                # Red shoulder pad
                pygame.draw.ellipse(surf, armor_red, (cx - 30, cy - 18, 22, 18))
                # Scimitar
                pts = [(cx + 15, cy + 5), (cx + 50, cy + 30), (cx + 40, cy + 45), (cx + 10, cy + 15)]
                pygame.draw.polygon(surf, sword_metal, pts)

            elif etype == "elite":
                # Full plate armor & Heavy scimitar
                # Large helmet with horns
                pygame.draw.ellipse(surf, helmet_blue, (cx - 22, head_y - 10, 44, 38))
                pygame.draw.polygon(surf, helmet_blue, [(cx, head_y - 30), (cx - 10, head_y - 6), (cx + 10, head_y - 6)])
                # Chest coins/medals from image
                for ry in [cy - 5, cy + 8, cy + 21]:
                    pygame.draw.circle(surf, (80, 80, 85), (cx, ry), 9)
                # Red tunic
                pygame.draw.rect(surf, armor_red, (cx - 22, cy + 10, 44, 25))
                # Heavy curved blade
                pts = [(cx + 20, cy - 10), (cx + 65, cy + 20), (cx + 55, cy + 55), (cx + 10, cy + 25)]
                pygame.draw.polygon(surf, sword_metal, pts)

            elif etype == "boss":
                # Prime Ascendant Orx — Golden crown, massive plate, twin scimitars
                # Ornate crown
                pygame.draw.ellipse(surf, (210, 180, 50), (cx - 28, head_y - 18, 56, 50))
                pygame.draw.polygon(surf, (210, 180, 50), [(cx, head_y - 45), (cx - 20, head_y - 12), (cx + 20, head_y - 12)])
                # Orange glowing eyes
                pygame.draw.circle(surf, (255, 120, 0), (cx - 10, head_y + 12), 6)
                pygame.draw.circle(surf, (255, 120, 0), (cx + 10, head_y + 12), 6)
                # Massive red chestplate with golden Orx seal
                pygame.draw.rect(surf, armor_red, (cx - 35, cy - 15, 70, 55))
                pygame.draw.circle(surf, (210, 180, 50), (cx, cy + 12), 18, 4)
                # Dual long scimitars
                for side in [-1, 1]:
                    x_start = cx + (side * 25)
                    pts = [(x_start, cy + 5), (x_start + (side * 50), cy + 45), (x_start + (side * 40), cy + 55), (x_start + (side * 5), cy + 15)]
                    pygame.draw.polygon(surf, sword_metal, pts)

            self.enemy_surfaces[etype] = surf

    # ------------------------------------------------------------------
    # Weapon sprite — DOOM BFG-ish orx blaster (bottom-centre)
    # ------------------------------------------------------------------

    def _generate_weapon(self) -> None:
        w, h = 220, 180
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        dark_metal = (45, 42, 50)
        mid_metal  = (72, 68, 80)
        hi_metal   = (110, 105, 120)
        glow_cyan  = (0,  200, 255)
        glow_amber = (220, 170, 40)

        # Main body — wide blocky receiver (DOOM-ish lower-right bulk)
        pygame.draw.rect(surf, dark_metal, (50, 60, 120,  90))   # body
        pygame.draw.rect(surf, mid_metal,  (55, 65, 110,  80))   # face
        pygame.draw.rect(surf, hi_metal,   (60, 68,  100,  10))  # top highlight

        # Barrel (stubby, centered)
        pygame.draw.rect(surf, dark_metal, (80,  30,  60,  38))  # barrel shroud
        pygame.draw.rect(surf, mid_metal,  (88,  34,  44,  28))
        pygame.draw.rect(surf, (10, 10, 12),(96, 28,  28,  12))  # muzzle recess

        # Glowing energy cell on left side
        pygame.draw.rect(surf, (0, 30, 60), (55, 90, 22, 40))
        for i in range(4):
            alpha_cell = 180 - i * 30
            cell_color = (*glow_cyan, alpha_cell)
            cell_surf  = pygame.Surface((18, 8), pygame.SRCALPHA)
            cell_surf.fill(cell_color)
            surf.blit(cell_surf, (57, 93 + i * 10))

        # Trigger guard
        pygame.draw.arc(surf, mid_metal,
                        pygame.Rect(90, 130, 40, 24), 3.14, 0, 4)

        # Side amber indicator light
        pygame.draw.circle(surf, glow_amber, (150, 90), 6)
        pygame.draw.circle(surf, (255, 230, 80), (150, 90), 3)

        # Grip
        pygame.draw.rect(surf, dark_metal, (100, 140, 28, 38))
        pygame.draw.rect(surf, (35, 32, 40), (104, 145, 20, 30))
        for i in range(4):
            pygame.draw.line(surf, hi_metal, (104, 148 + i * 7), (124, 148 + i * 7), 1)

        self.weapon_surface = surf

        # Muzzle flash — cyan-amber Orx plasma burst
        flash = pygame.Surface((60, 60), pygame.SRCALPHA)
        cx, cy = 30, 30
        for r in range(30, 0, -1):
            t     = r / 30
            alpha = int(255 * t)
            ri    = int(0   + (220 - 0)   * t)
            gi    = int(200 + (200 - 200) * t)
            bi    = int(255 + (40  - 255) * t)
            pygame.draw.circle(flash, (ri, gi, bi, alpha), (cx, cy), r)
        self.muzzle_flash_surface = flash
