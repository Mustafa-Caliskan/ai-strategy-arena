"""
pixel_atlas.py — WorldBox Tarzı Saf Pixel Art Sprite Fabrikası ve Önbelleği

İçerik:
- 4 Farklı Piksel Asker Sınıfı (🛡️ Piyade, 🏹 Okçu, 🐎 Süvari, ☄️ Mancınık)
- Piksel Uçan Mermiler (Oklar ve Mancınık Kayaları)
- Piksel Can Barı (HP Bar) ve Gölgeler
- Piksel Ağaçlar, Kayalar, Madenler ve Binalar (Köy Evi, Saray, Çiftlik, Kereste, Maden, Kale)
"""
from __future__ import annotations

import math
import pygame
from typing import Optional
from game.entities import UnitClass


class PixelAtlas:
    """Tüm pixel art sprite'larını tek bir merkezi fabrikada üretir ve önbellekler."""

    _instance: Optional["PixelAtlas"] = None
    _cache: dict[str, pygame.Surface] = {}

    @classmethod
    def get(cls) -> "PixelAtlas":
        if cls._instance is None:
            cls._instance = PixelAtlas()
        return cls._instance

    def __init__(self):
        self._build_all_sprites()

    def get_sprite(self, key: str) -> pygame.Surface:
        return self._cache.get(key, self._cache["missing"])

    def _build_all_sprites(self):
        # 1. Fallback sprite
        missing = pygame.Surface((16, 16), pygame.SRCALPHA)
        missing.fill((255, 0, 255))
        self._cache["missing"] = missing

        # 2. Ağaçlar
        self._cache["pine_large"] = self._create_pine_tree(size="large")
        self._cache["pine_medium"] = self._create_pine_tree(size="medium")
        self._cache["pine_small"] = self._create_pine_tree(size="small")
        self._cache["oak_large"] = self._create_oak_tree(size="large")
        self._cache["oak_medium"] = self._create_oak_tree(size="medium")
        self._cache["bush"] = self._create_bush()

        # 3. Kayalar ve Cevherler
        self._cache["rock_large"] = self._create_rock(size="large")
        self._cache["rock_small"] = self._create_rock(size="small")
        self._cache["ore_gold"] = self._create_ore(ore_type="gold")
        self._cache["ore_iron"] = self._create_ore(ore_type="iron")

        # 4. Binalar
        self._cache["bld_house"] = self._create_house()
        self._cache["bld_city_hall"] = self._create_city_hall()
        self._cache["bld_capital_palace"] = self._create_capital_palace()
        self._cache["bld_farm"] = self._create_farm()
        self._cache["bld_lumber"] = self._create_lumber()
        self._cache["bld_mine"] = self._create_mine()
        self._cache["bld_fort"] = self._create_fort()

        # 5. Gölgeler ve Mermiler
        self._cache["unit_shadow"] = self._create_shadow(w=14, h=6)
        self._cache["cav_shadow"] = self._create_shadow(w=22, h=8)
        self._cache["tree_shadow"] = self._create_shadow(w=20, h=8)
        self._cache["bld_shadow"] = self._create_shadow(w=28, h=10)
        self._cache["arrow"] = self._create_arrow()
        self._cache["boulder"] = self._create_boulder()

    # ── Gölgeler ve Mermiler ────────────────────────────────────────

    def _create_shadow(self, w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (10, 12, 18, 110), (0, 0, w, h))
        return surf

    def _create_arrow(self) -> pygame.Surface:
        surf = pygame.Surface((10, 4), pygame.SRCALPHA)
        pygame.draw.line(surf, (140, 100, 50), (0, 2), (8, 2), 1)
        pygame.draw.polygon(surf, (220, 220, 230), [(8, 0), (10, 2), (8, 4)])
        return surf

    def _create_boulder(self) -> pygame.Surface:
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(surf, (90, 80, 70), (4, 4), 3)
        pygame.draw.circle(surf, (140, 130, 115), (3, 3), 1)
        return surf

    # ── Doğal Çevre ─────────────────────────────────────────────────

    def _create_pine_tree(self, size: str = "large") -> pygame.Surface:
        w, h = (24, 32) if size == "large" else ((18, 26) if size == "medium" else (14, 20))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        trunk_w = 4 if size == "large" else 2
        trunk_h = 8 if size == "large" else 6
        pygame.draw.rect(surf, (45, 30, 15), (cx - trunk_w // 2, h - trunk_h, trunk_w, trunk_h))

        tiers = [(h - 8, w // 2 - 1, 8), (h - 14, w // 2 - 3, 7), (h - 20, w // 2 - 5, 6)] if size == "large" else [(h - 6, w // 2 - 1, 6), (h - 11, w // 2 - 2, 5), (h - 16, w // 2 - 4, 5)]
        dark_green, mid_green, light_green = (14, 62, 22), (24, 102, 38), (42, 142, 56)

        for by, radius, th in tiers:
            pygame.draw.polygon(surf, dark_green, [(cx, by - th), (cx - radius, by), (cx + radius, by)])
            pygame.draw.polygon(surf, mid_green, [(cx, by - th), (cx - radius + 1, by - 1), (cx + radius - 1, by - 1)])
            pygame.draw.polygon(surf, light_green, [(cx, by - th), (cx - radius + 1, by - 1), (cx, by - 1)])

        return surf

    def _create_oak_tree(self, size: str = "large") -> pygame.Surface:
        w, h = (28, 32) if size == "large" else (22, 26)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        pygame.draw.rect(surf, (60, 42, 25), (cx - 2, h - 10, 5, 10))
        pygame.draw.circle(surf, (16, 70, 26), (cx - 6, h - 14), 7)
        pygame.draw.circle(surf, (16, 70, 26), (cx + 6, h - 14), 7)
        pygame.draw.circle(surf, (16, 70, 26), (cx, h - 18), 9)
        pygame.draw.circle(surf, (30, 115, 42), (cx - 5, h - 15), 6)
        pygame.draw.circle(surf, (30, 115, 42), (cx + 5, h - 15), 6)
        pygame.draw.circle(surf, (30, 115, 42), (cx, h - 19), 8)
        pygame.draw.circle(surf, (52, 158, 64), (cx - 4, h - 17), 5)
        return surf

    def _create_bush(self) -> pygame.Surface:
        surf = pygame.Surface((12, 10), pygame.SRCALPHA)
        pygame.draw.circle(surf, (18, 75, 28), (4, 6), 4)
        pygame.draw.circle(surf, (18, 75, 28), (8, 6), 4)
        pygame.draw.circle(surf, (35, 125, 48), (6, 4), 4)
        return surf

    def _create_rock(self, size: str = "large") -> pygame.Surface:
        w, h = (18, 14) if size == "large" else (12, 10)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (75, 65, 55), [(2, h - 2), (w - 2, h - 2), (w - 4, 3), (4, 2)])
        pygame.draw.polygon(surf, (115, 100, 85), [(3, h - 3), (w - 4, h - 3), (w - 6, 4), (5, 3)])
        return surf

    def _create_ore(self, ore_type: str = "gold") -> pygame.Surface:
        surf = pygame.Surface((14, 12), pygame.SRCALPHA)
        pygame.draw.circle(surf, (60, 50, 42), (7, 6), 5)
        ore_color = (255, 215, 40) if ore_type == "gold" else (195, 205, 220)
        pygame.draw.circle(surf, ore_color, (5, 5), 2)
        pygame.draw.circle(surf, ore_color, (9, 7), 2)
        return surf

    # ── Binalar ─────────────────────────────────────────────────────

    def _create_house(self) -> pygame.Surface:
        surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.rect(surf, (155, 135, 110), (4, 10, 16, 12), border_radius=1)
        pygame.draw.polygon(surf, (168, 52, 36), [(2, 10), (12, 2), (22, 10)])
        pygame.draw.rect(surf, (65, 40, 20), (10, 15, 4, 7))
        pygame.draw.rect(surf, (255, 225, 100), (5, 13, 3, 3))
        pygame.draw.rect(surf, (255, 225, 100), (16, 13, 3, 3))
        return surf

    def _create_city_hall(self) -> pygame.Surface:
        surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(surf, (142, 130, 118), (4, 12, 24, 18), border_radius=2)
        pygame.draw.rect(surf, (120, 110, 100), (4, 4, 8, 26))
        pygame.draw.polygon(surf, (155, 45, 30), [(3, 4), (8, 0), (13, 4)])
        pygame.draw.polygon(surf, (185, 58, 40), [(11, 12), (22, 5), (29, 12)])
        pygame.draw.rect(surf, (255, 230, 110), (6, 8, 4, 4))
        pygame.draw.rect(surf, (255, 230, 110), (16, 15, 4, 4))
        pygame.draw.rect(surf, (50, 32, 18), (18, 22, 6, 8))
        return surf

    def _create_capital_palace(self) -> pygame.Surface:
        surf = pygame.Surface((36, 36), pygame.SRCALPHA)
        pygame.draw.rect(surf, (130, 125, 135), (4, 10, 28, 24), border_radius=2)
        pygame.draw.rect(surf, (110, 105, 118), (2, 6, 8, 28))
        pygame.draw.rect(surf, (110, 105, 118), (26, 6, 8, 28))
        pygame.draw.polygon(surf, (215, 45, 45), [(10, 10), (18, 2), (26, 10)])
        pygame.draw.line(surf, (60, 50, 40), (18, 2), (18, -2), 2)
        pygame.draw.polygon(surf, (255, 215, 40), [(18, 0), (25, 2), (18, 5)])
        pygame.draw.rect(surf, (40, 35, 45), (14, 20, 8, 14), border_top_left_radius=4, border_top_right_radius=4)
        return surf

    def _create_farm(self) -> pygame.Surface:
        surf = pygame.Surface((28, 26), pygame.SRCALPHA)
        pygame.draw.rect(surf, (218, 185, 55), (2, 8, 24, 16), border_radius=3)
        pygame.draw.rect(surf, (140, 60, 40), (10, 4, 8, 12))
        pygame.draw.polygon(surf, (100, 40, 25), [(8, 4), (14, 0), (20, 4)])
        return surf

    def _create_lumber(self) -> pygame.Surface:
        surf = pygame.Surface((26, 22), pygame.SRCALPHA)
        pygame.draw.rect(surf, (95, 60, 28), (4, 6, 18, 14), border_radius=2)
        pygame.draw.polygon(surf, (70, 40, 18), [(2, 6), (13, 1), (24, 6)])
        return surf

    def _create_mine(self) -> pygame.Surface:
        surf = pygame.Surface((26, 24), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (70, 58, 48), [(2, 22), (13, 4), (24, 22)])
        pygame.draw.rect(surf, (16, 12, 10), (7, 12, 12, 10))
        return surf

    def _create_fort(self) -> pygame.Surface:
        surf = pygame.Surface((26, 26), pygame.SRCALPHA)
        pygame.draw.rect(surf, (115, 115, 125), (4, 8, 18, 16), border_radius=2)
        pygame.draw.polygon(surf, (215, 45, 45), [(13, 0), (19, 2), (13, 5)])
        return surf

    # ── Taktiksel Asker Sınıfları Sprite'ları (4 Unit Classes) ───────

    def get_unit_sprite(
        self,
        owner: str,
        color: tuple[int, int, int],
        unit_class: UnitClass = UnitClass.INFANTRY,
        anim_frame: int = 0,
        is_combat: bool = False,
    ) -> pygame.Surface:
        """Sınıfa özel piksel asker sprite'ı üretir."""
        cache_key = f"unit_{owner}_{color}_{unit_class.value}_{anim_frame}_{is_combat}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        bob = 1 if anim_frame == 1 else 0

        # 1. 🛡️ PİYADE (INFANTRY)
        if unit_class == UnitClass.INFANTRY:
            surf = pygame.Surface((20, 22), pygame.SRCALPHA)
            cx, cy = 10, 11 + bob
            # Kask
            pygame.draw.circle(surf, (190, 195, 205), (cx, cy - 5), 4)
            pygame.draw.rect(surf, (120, 125, 135), (cx - 4, cy - 6, 8, 3))
            # Zırh
            pygame.draw.rect(surf, color, (cx - 3, cy - 1, 6, 6), border_radius=1)
            # Ayaklar
            pygame.draw.rect(surf, (60, 50, 40), (cx - 3, cy + 5, 2, 3))
            pygame.draw.rect(surf, (60, 50, 40), (cx + 1, cy + 5, 2, 3))
            # Kalkan
            pygame.draw.rect(surf, (30, 30, 40), (cx - 7, cy - 2, 4, 7), border_radius=1)
            pygame.draw.rect(surf, color, (cx - 6, cy - 1, 2, 5))
            # Kılıç
            if is_combat:
                pygame.draw.line(surf, (225, 230, 240), (cx + 4, cy - 2), (cx + 9, cy - 8), 2)
            else:
                pygame.draw.line(surf, (200, 205, 215), (cx + 4, cy), (cx + 4, cy - 6), 2)

        # 2. 🏹 OKÇU (ARCHER)
        elif unit_class == UnitClass.ARCHER:
            surf = pygame.Surface((20, 22), pygame.SRCALPHA)
            cx, cy = 10, 11 + bob
            # Yeşil kapüşon / tüy
            pygame.draw.circle(surf, (45, 95, 45), (cx, cy - 5), 4)
            pygame.draw.polygon(surf, (215, 55, 40), [(cx + 2, cy - 7), (cx + 5, cy - 10), (cx + 3, cy - 6)])
            # Deri zırh
            pygame.draw.rect(surf, color, (cx - 3, cy - 1, 6, 6), border_radius=1)
            # Ayaklar
            pygame.draw.rect(surf, (85, 60, 35), (cx - 3, cy + 5, 2, 3))
            pygame.draw.rect(surf, (85, 60, 35), (cx + 1, cy + 5, 2, 3))
            # Yay (Bow)
            pygame.draw.arc(surf, (150, 100, 45), (cx - 7, cy - 4, 6, 10), 1.57, 4.71, 2)
            pygame.draw.line(surf, (230, 230, 240), (cx - 4, cy - 4), (cx - 4, cy + 6), 1)
            # Sadağın okları
            pygame.draw.line(surf, (210, 180, 80), (cx + 3, cy - 3), (cx + 6, cy - 7), 1)

        # 3. 🐎 SÜVARİ (CAVALRY)
        elif unit_class == UnitClass.CAVALRY:
            surf = pygame.Surface((28, 24), pygame.SRCALPHA)
            cx, cy = 14, 12 + bob
            # Zırhlı At gövdesi
            pygame.draw.ellipse(surf, (120, 75, 45), (cx - 10, cy, 20, 9))
            pygame.draw.ellipse(surf, (110, 65, 38), (cx + 6, cy - 5, 6, 10))  # At başı
            # At bacakları
            pygame.draw.rect(surf, (70, 40, 20), (cx - 8, cy + 7, 2, 5))
            pygame.draw.rect(surf, (70, 40, 20), (cx - 3, cy + 7, 2, 5))
            pygame.draw.rect(surf, (70, 40, 20), (cx + 3, cy + 7, 2, 5))
            pygame.draw.rect(surf, (70, 40, 20), (cx + 7, cy + 7, 2, 5))
            # Süvari Şövalye
            pygame.draw.circle(surf, (190, 195, 205), (cx - 2, cy - 6), 4)  # Kask
            pygame.draw.rect(surf, color, (cx - 5, cy - 2, 7, 5))          # Zırh
            # Uzun Mızrak (Lance)
            pygame.draw.line(surf, (180, 140, 60), (cx - 4, cy), (cx + 12, cy - 5), 2)
            pygame.draw.polygon(surf, (225, 230, 245), [(cx + 12, cy - 7), (cx + 15, cy - 5), (cx + 12, cy - 3)])

        # 4. ☄️ MANCINIK (CATAPULT)
        elif unit_class == UnitClass.CATAPULT:
            surf = pygame.Surface((26, 24), pygame.SRCALPHA)
            cx, cy = 13, 12
            # Ahşap şasi
            pygame.draw.rect(surf, (110, 70, 35), (cx - 9, cy, 18, 6), border_radius=1)
            # Taş/Demir tekerlekler
            pygame.draw.circle(surf, (60, 60, 70), (cx - 7, cy + 6), 3)
            pygame.draw.circle(surf, (60, 60, 70), (cx + 7, cy + 6), 3)
            # Fırlatma kolu ve kaya
            pygame.draw.line(surf, (135, 90, 45), (cx - 4, cy + 2), (cx + 6, cy - 7), 3)
            pygame.draw.circle(surf, (90, 80, 70), (cx + 7, cy - 8), 4)

        else:
            surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (8, 8), 6)

        self._cache[cache_key] = surf
        return surf

    def get_envoy_sprite(self, owner: str, color: tuple[int, int, int], anim_frame: int = 0) -> pygame.Surface:
        cache_key = f"envoy_{owner}_{color}_{anim_frame}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        surf = pygame.Surface((18, 20), pygame.SRCALPHA)
        cx, cy = 9, 10 + (1 if anim_frame == 1 else 0)
        pygame.draw.circle(surf, color, (cx, cy - 4), 4)
        pygame.draw.circle(surf, (240, 210, 180), (cx, cy - 3), 2)
        pygame.draw.polygon(surf, color, [(cx - 4, cy - 1), (cx + 4, cy - 1), (cx + 5, cy + 6), (cx - 5, cy + 6)])
        pygame.draw.rect(surf, (245, 242, 230), (cx + 2, cy, 5, 4))
        pygame.draw.circle(surf, (215, 45, 45), (cx + 4, cy + 2), 1)
        pygame.draw.line(surf, (160, 120, 60), (cx - 4, cy - 5), (cx - 4, cy + 6), 2)
        pygame.draw.circle(surf, (100, 220, 255), (cx - 4, cy - 5), 2)

        self._cache[cache_key] = surf
        return surf