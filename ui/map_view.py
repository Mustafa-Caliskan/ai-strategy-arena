"""
map_view.py — WorldBox Tarzı Yaşayan Piksel Strateji Haritası (Pixel-Art Engine)

İki katmanlı çizim mimarisi:
  - draw_terrain(): Statik zemin (PixelAtlas ile piksel çimenler, 8-neighbor kıyı autotiling,
    katmanlı piksel ağaçlar, granit dağlar, taş yollar, orta çağ evleri ve kaleler)
    verilen yüzeye çizilir. TerrainRenderer tarafından önbelleğe alınır.
  - draw_dynamic(): Her frame çizilen dinamik katmanlar (ülke sınırları, canlı nefes alan başkent aurası).

Bu modül simülasyon state'ini ASLA mutate etmez; yalnızca okur.
"""
from __future__ import annotations

import math
import time
import pygame
from typing import TYPE_CHECKING

from game.buildings import BuildingType
from render.pixel_atlas import PixelAtlas
from render.wesnoth_atlas import WesnothAtlas

if TYPE_CHECKING:
    from game.map import GameMap, Tile, TileType
    from game.country import Country
    from render.camera import Camera


# ── Tile Renk Paleti (WorldBox / Civilization Doğal Doğa Teması) ────
TILE_COLORS = {
    "land":     (142, 178, 102),  # Taze yeşil çayır
    "forest":   ( 74, 126,  62),  # Zümrüt orman yeşili
    "mountain": (132, 124, 114),  # Granit kaya grisi
    "water":    ( 52, 128, 188),  # Berrak nehir mavisi
    "mine":     (120, 108,  98),  # Demir/taş madeni
    "city":     (202, 188, 158),
}

TILE_BORDER = {
    "land":     (135, 168, 100),
    "water":    (36,   84, 134),
    "forest":   (16,   72,  26),
    "mountain": (106,  86,  68),
    "mine":     (152, 122,  30),
    "city":     (175, 162, 132),
}


def _tile_hash(x: int, y: int) -> int:
    """Tile koordinatlarından deterministik hash üretir (flicker önleme)."""
    return (x * 73856093 ^ y * 19349663) & 0xFFFFFF


class MapView:
    """WorldBox tarzı yaşayan piksel strateji haritasını çizer."""

    TILE_SIZE = 36
    BORDER_WIDTH = 1

    def __init__(self, map_width: int = 20, map_height: int = 20):
        self.map_width = map_width
        self.map_height = map_height
        self.tile_size = self.TILE_SIZE
        self.surface_width  = map_width  * self.tile_size
        self.surface_height = map_height * self.tile_size
        self.atlas = PixelAtlas.get()
        self.wesnoth_atlas = WesnothAtlas.get()

    # ── Statik Terrain (Önbelleğe Alınır) ────────────────────────────

    def draw_terrain(
        self,
        surface: pygame.Surface,
        game_map: "GameMap",
        countries: list["Country"],
    ) -> None:
        """Statik terrain'i verilen yüzeye çizer (tile + autotiling + geçişler + yol + bina)."""
        country_colors = {c.agent_id: c.color for c in countries}

        # 1. Zemin ve arazi
        for col in game_map.tiles:
            for tile in col:
                self._draw_tile(surface, tile, country_colors, game_map)

        # 2. Yollar (organik altyapı ağı)
        self._draw_roads(surface, game_map)

        # 3. Binalar ve yerleşimler
        for col in game_map.tiles:
            for tile in col:
                if tile.building:
                    self._draw_building(surface, tile)

    # ── Dinamik Katman (Her Frame Kamera ile) ────────────────────────

    def draw_dynamic(
        self,
        surface: pygame.Surface,
        game_map: "GameMap",
        countries: list["Country"],
        camera: "Camera",
    ) -> None:
        """Kamera dönüşümüyle dinamik katmanları çizer (sınırlar + başkentler)."""
        country_colors = {c.agent_id: c.color for c in countries}

        # Doğal ülke sınırları
        self._draw_borders(surface, game_map, country_colors, camera)

        # Görkemli başkent sancakları
        for country in countries:
            if country.is_active():
                self._draw_capital(surface, country, camera)

    # ── Çizim Yardımcıları ──────────────────────────────────────────

    def _draw_tile(self, surface: pygame.Surface, tile: "Tile", country_colors: dict, game_map: "GameMap") -> None:
        from game.map import TileType
        x = tile.x * self.tile_size
        y = tile.y * self.tile_size
        w = h = self.tile_size
        th = _tile_hash(tile.x, tile.y)

        base_color = TILE_COLORS.get(tile.tile_type.value, (180, 180, 180))

        # Deterministik hafif ton varyasyonu (organik kıta zemin dokusu)
        var = (th % 7) - 3
        base_color = (
            max(0, min(255, base_color[0] + var)),
            max(0, min(255, base_color[1] + var)),
            max(0, min(255, base_color[2] + var)),
        )

        pygame.draw.rect(surface, base_color, (x, y, w, h))

        # Ülke sahipliği (yumuşak ve net renk harmanı)
        if tile.owner and tile.owner in country_colors:
            owner_color = country_colors[tile.owner]
            blended = (
                int(base_color[0] * 0.70 + owner_color[0] * 0.30),
                int(base_color[1] * 0.70 + owner_color[1] * 0.30),
                int(base_color[2] * 0.70 + owner_color[2] * 0.30),
            )
            pygame.draw.rect(surface, blended, (x, y, w, h))

        # 8-Neighbor Organik Kıyı Autotiling
        if tile.tile_type == TileType.WATER:
            self._draw_water_autotile(surface, tile, x, y, w, h, game_map)
        else:
            self._draw_terrain_transitions(surface, tile, x, y, w, h, game_map, th)

        # Doğal arazi iç detayları & Pixel Sprite yerleşimi
        self._draw_terrain_detail(surface, tile, x, y, w, h, th)

        # Seamless sınırlar (Yalnızca farklı biyom veya farklı sahiplik sınırında çiz)
        self._draw_seamless_tile_borders(surface, tile, x, y, w, h, game_map)

    def _draw_water_autotile(self, surface: pygame.Surface, tile: "Tile", x: int, y: int, w: int, h: int, game_map: "GameMap") -> None:
        """8-Neighbor autotiling ile organik koylar, kumsallar ve kavisli kıyılar çizer."""
        from game.map import TileType
        sand_color = (214, 200, 152)
        shallow_water = (68, 142, 198)
        deep_edge = (88, 162, 218)

        up = game_map.get_tile(tile.x, tile.y - 1)
        down = game_map.get_tile(tile.x, tile.y + 1)
        left = game_map.get_tile(tile.x - 1, tile.y)
        right = game_map.get_tile(tile.x + 1, tile.y)

        has_up = up and up.tile_type != TileType.WATER
        has_down = down and down.tile_type != TileType.WATER
        has_left = left and left.tile_type != TileType.WATER
        has_right = right and right.tile_type != TileType.WATER

        if has_up:
            pygame.draw.line(surface, sand_color, (x, y), (x + w, y), 2)
            pygame.draw.line(surface, shallow_water, (x, y + 2), (x + w, y + 2), 2)
            pygame.draw.line(surface, deep_edge, (x, y + 4), (x + w, y + 4), 1)
        if has_down:
            pygame.draw.line(surface, sand_color, (x, y + h - 1), (x + w, y + h - 1), 2)
            pygame.draw.line(surface, shallow_water, (x, y + h - 3), (x + w, y + h - 3), 2)
            pygame.draw.line(surface, deep_edge, (x, y + h - 5), (x + w, y + h - 5), 1)
        if has_left:
            pygame.draw.line(surface, sand_color, (x, y), (x, y + h), 2)
            pygame.draw.line(surface, shallow_water, (x + 2, y), (x + 2, y + h), 2)
            pygame.draw.line(surface, deep_edge, (x + 4, y), (x + 4, y + h), 1)
        if has_right:
            pygame.draw.line(surface, sand_color, (x + w - 1, y), (x + w - 1, y + h), 2)
            pygame.draw.line(surface, shallow_water, (x + w - 3, y), (x + w - 3, y + h), 2)
            pygame.draw.line(surface, deep_edge, (x + w - 5, y), (x + w - 5, y + h), 1)

        # Çapraz Köşeler
        nw = game_map.get_tile(tile.x - 1, tile.y - 1)
        if nw and nw.tile_type != TileType.WATER and not (has_up or has_left):
            pygame.draw.polygon(surface, sand_color, [(x, y), (x + 5, y), (x, y + 5)])
            pygame.draw.polygon(surface, shallow_water, [(x + 5, y), (x + 8, y), (x, y + 8), (x, y + 5)])

        ne = game_map.get_tile(tile.x + 1, tile.y - 1)
        if ne and ne.tile_type != TileType.WATER and not (has_up or has_right):
            pygame.draw.polygon(surface, sand_color, [(x + w, y), (x + w - 5, y), (x + w, y + 5)])
            pygame.draw.polygon(surface, shallow_water, [(x + w - 5, y), (x + w - 8, y), (x + w, y + 8), (x + w, y + 5)])

        sw = game_map.get_tile(tile.x - 1, tile.y + 1)
        if sw and sw.tile_type != TileType.WATER and not (has_down or has_left):
            pygame.draw.polygon(surface, sand_color, [(x, y + h), (x + 5, y + h), (x, y + h - 5)])
            pygame.draw.polygon(surface, shallow_water, [(x + 5, y + h), (x + 8, y + h), (x, y + h - 8), (x, y + h - 5)])

        se = game_map.get_tile(tile.x + 1, tile.y + 1)
        if se and se.tile_type != TileType.WATER and not (has_down or has_right):
            pygame.draw.polygon(surface, sand_color, [(x + w, y + h), (x + w - 5, y + h), (x + w, y + h - 5)])
            pygame.draw.polygon(surface, shallow_water, [(x + w - 5, y + h), (x + w - 8, y + h), (x + w, y + h - 8), (x + w, y + h - 5)])

    def _draw_terrain_transitions(self, surface: pygame.Surface, tile: "Tile", x: int, y: int, w: int, h: int, game_map: "GameMap", th: int) -> None:
        """Araziler arası yumuşak sınır geçiş detayları."""
        from game.map import TileType
        if tile.tile_type != TileType.LAND or tile.building:
            return

        # Komşu orman varsa kenara küçük çalı/fidan sprite'ı blitle
        for dx, dy, ox, oy in [(-1, 0, 2, h // 2 - 4), (1, 0, w - 12, h // 2 - 4), (0, -1, w // 2 - 6, 2), (0, 1, w // 2 - 6, h - 10)]:
            nb = game_map.get_tile(tile.x + dx, tile.y + dy)
            if nb and nb.tile_type == TileType.FOREST:
                bush = self.atlas.get_sprite("bush")
                surface.blit(bush, (x + ox, y + oy))

        # Komşu dağ varsa eteklerine kaya döküntüsü sprite'ı blitle
        for dx, dy, ox, oy in [(-1, 0, 3, h // 2 - 2), (1, 0, w - 14, h // 2 - 2), (0, -1, w // 2 - 6, 3), (0, 1, w // 2 - 6, h - 12)]:
            nb = game_map.get_tile(tile.x + dx, tile.y + dy)
            if nb and nb.tile_type == TileType.MOUNTAIN:
                rock = self.atlas.get_sprite("rock_small")
                surface.blit(rock, (x + ox, y + oy))

    def _draw_seamless_tile_borders(self, surface: pygame.Surface, tile: "Tile", x: int, y: int, w: int, h: int, game_map: "GameMap") -> None:
        """Grid çizgilerini kaldırarak tamamen organik birleşik kıta haritası oluşturur."""
        pass

    def _draw_terrain_detail(self, surface: pygame.Surface, tile: "Tile", x: int, y: int, w: int, h: int, th: int) -> None:
        from game.map import TileType
        cx, cy = x + w // 2, y + h // 2

        if tile.tile_type == TileType.LAND and not tile.building:
            # Prosedürel çimen stipples ve minik çalılar
            g_col = (124, 160, 88)
            ox1 = (th % 7) - 3
            oy1 = ((th >> 3) % 7) - 3
            pygame.draw.line(surface, g_col, (cx + ox1 - 5, cy + oy1 + 3), (cx + ox1 - 4, cy + oy1), 1)
            pygame.draw.line(surface, g_col, (cx + ox1 - 4, cy + oy1), (cx + ox1 - 3, cy + oy1 + 3), 1)

            if (th % 5) == 0:
                bush = self.atlas.get_sprite("bush")
                surface.blit(bush, (cx + ox1 - 6, cy + oy1 - 4))
            elif (th % 4) == 0:
                rock = self.atlas.get_sprite("rock_small")
                surface.blit(rock, (cx - 6, cy - 4))

        elif tile.tile_type == TileType.FOREST and not tile.building:
            # WorldBox Tarzı Katmanlı Piksel Ağaç Korusu (Zemin gölgesi + Çam / Meşe)
            style = th % 3
            t_shadow = self.atlas.get_sprite("tree_shadow")

            if style == 0:
                # 2 Katmanlı Büyük Çam Korusu
                surface.blit(t_shadow, (cx - 10, cy + 6))
                pine_l = self.atlas.get_sprite("pine_large")
                pine_s = self.atlas.get_sprite("pine_small")
                surface.blit(pine_l, (cx - 12, cy - 16))
                surface.blit(pine_s, (cx + 1, cy - 8))
            elif style == 1:
                # Meşe Korusu & Çalılar
                surface.blit(t_shadow, (cx - 10, cy + 6))
                oak_l = self.atlas.get_sprite("oak_large")
                surface.blit(oak_l, (cx - 14, cy - 16))
                bush = self.atlas.get_sprite("bush")
                surface.blit(bush, (cx + 4, cy + 4))
            else:
                # İkiz Çamlar
                surface.blit(t_shadow, (cx - 10, cy + 6))
                pine_m = self.atlas.get_sprite("pine_medium")
                surface.blit(pine_m, (cx - 11, cy - 12))
                surface.blit(pine_m, (cx - 1, cy - 10))

        elif tile.tile_type == TileType.MOUNTAIN and not tile.building:
            # Heybetli Wesnoth Granit Dağ Zirvesi
            mountain = pygame.transform.scale(self.wesnoth_atlas.get_terrain_sprite("mountain"), (34, 34))
            surface.blit(mountain, (cx - 17, cy - 18))

        elif tile.tile_type == TileType.MINE and not tile.building:
            # Maden ocağı iskelesi & altın/demir cevheri
            mine_bld = self.atlas.get_sprite("bld_mine")
            surface.blit(mine_bld, (cx - 13, cy - 12))
            ore = self.atlas.get_sprite("ore_gold" if (th % 2 == 0) else "ore_iron")
            surface.blit(ore, (cx + 3, cy + 3))

        elif tile.tile_type == TileType.WATER:
            # Canlı kavisli su dalgaları
            oy = (th % 5) - 2
            pygame.draw.arc(surface, (98, 162, 220), (x + 3, cy - 6 + oy, 15, 6), 3.14, 0, 2)
            pygame.draw.arc(surface, (98, 162, 220), (x + w - 18, cy + 2 + oy, 15, 6), 3.14, 0, 2)

    def _draw_roads(self, surface: pygame.Surface, game_map: "GameMap") -> None:
        """Çift katmanlı (çakıl ve zemin) organik altyapı yollarını çizer."""
        ts = self.tile_size
        road_outer = (128, 98, 62)
        road_inner = (185, 155, 110)
        for col in game_map.tiles:
            for tile in col:
                if not tile.has_road and not (tile.building and tile.building.building_type in (BuildingType.CITY, BuildingType.FORT)):
                    continue
                cx = tile.x * ts + ts // 2
                cy = tile.y * ts + ts // 2

                if tile.has_road:
                    pygame.draw.circle(surface, road_outer, (cx, cy), 4)
                    pygame.draw.circle(surface, road_inner, (cx, cy), 2)

                    right = game_map.get_tile(tile.x + 1, tile.y)
                    if right and (right.has_road or right.building):
                        pygame.draw.line(surface, road_outer, (cx, cy), (cx + ts, cy), 4)
                        pygame.draw.line(surface, road_inner, (cx, cy), (cx + ts, cy), 2)
                    below = game_map.get_tile(tile.x, tile.y + 1)
                    if below and (below.has_road or below.building):
                        pygame.draw.line(surface, road_outer, (cx, cy), (cx, cy + ts), 4)
                        pygame.draw.line(surface, road_inner, (cx, cy), (cx, cy + ts), 2)

    def _draw_building(self, surface: pygame.Surface, tile: "Tile") -> None:
        ts = self.tile_size
        cx = tile.x * ts + ts // 2
        cy = tile.y * ts + ts // 2
        b = tile.building
        btype = b.building_type

        if btype == BuildingType.FARM:
            # Wesnoth Köyü
            village = pygame.transform.scale(self.wesnoth_atlas.get_terrain_sprite("village"), (34, 34))
            surface.blit(village, (cx - 17, cy - 18))
        elif btype == BuildingType.LUMBER_MILL:
            village = pygame.transform.scale(self.wesnoth_atlas.get_terrain_sprite("village"), (32, 32))
            surface.blit(village, (cx - 16, cy - 17))
        elif btype == BuildingType.MINE:
            mine = self.atlas.get_sprite("bld_mine")
            surface.blit(mine, (cx - 13, cy - 12))
        elif btype == BuildingType.FORT:
            # Wesnoth Taş Kalesi / Harabeler
            ruins = pygame.transform.scale(self.wesnoth_atlas.get_terrain_sprite("ruins"), (38, 38))
            surface.blit(ruins, (cx - 19, cy - 20))
        elif btype == BuildingType.CITY:
            # Wesnoth Heybetli Kraliyet Kalesi
            castle = pygame.transform.scale(self.wesnoth_atlas.get_terrain_sprite("castle"), (46, 46))
            surface.blit(castle, (cx - 23, cy - 26))

    def _draw_borders(self, surface: pygame.Surface, game_map: "GameMap", country_colors: dict, camera: "Camera") -> None:
        """Kamera dönüşümüyle yumuşak ve net ülke sınırlarını çizer."""
        ts = self.tile_size
        for col in game_map.tiles:
            for tile in col:
                if not tile.owner:
                    continue
                border_col = country_colors.get(tile.owner, (255, 255, 255))
                right = game_map.get_tile(tile.x + 1, tile.y)
                if right and right.owner != tile.owner:
                    x0, y0 = camera.world_to_screen((tile.x + 1) * ts, tile.y * ts)
                    x1, y1 = camera.world_to_screen((tile.x + 1) * ts, (tile.y + 1) * ts)
                    pygame.draw.line(surface, (12, 12, 20), (x0, y0), (x1, y1), 3)
                    pygame.draw.line(surface, border_col, (x0, y0), (x1, y1), 2)
                below = game_map.get_tile(tile.x, tile.y + 1)
                if below and below.owner != tile.owner:
                    x0, y0 = camera.world_to_screen(tile.x * ts, (tile.y + 1) * ts)
                    x1, y1 = camera.world_to_screen((tile.x + 1) * ts, (tile.y + 1) * ts)
                    pygame.draw.line(surface, (12, 12, 20), (x0, y0), (x1, y1), 3)
                    pygame.draw.line(surface, border_col, (x0, y0), (x1, y1), 2)

    def _draw_capital(self, surface: pygame.Surface, country: "Country", camera: "Camera") -> None:
        """Görkemli, altın taçlı ve nefes alan (pulse glow) başkent sarayı."""
        cx, cy = camera.world_to_screen(
            country.capital_x * self.tile_size + self.tile_size // 2,
            country.capital_y * self.tile_size + self.tile_size // 2,
        )
        r = country.color

        pulse = int(math.sin(time.perf_counter() * 3.5) * 2)

        # 1. Dış altın hale / glow
        pygame.draw.circle(surface, (255, 215, 0), (int(cx), int(cy)), max(12, 16 + pulse), 1)
        # 2. Kalın koyu kalkan çerçevesi
        pygame.draw.circle(surface, (12, 12, 18), (int(cx), int(cy)), 14)
        # 3. Altın kraliyet halkası
        pygame.draw.circle(surface, (255, 215, 0), (int(cx), int(cy)), 12)
        # 4. Ülke rengi çekirdek
        pygame.draw.circle(surface, r, (int(cx), int(cy)), 9)
        # 5. Merkez altın kraliyet tacı / yıldız
        pygame.draw.circle(surface, (255, 242, 130), (int(cx), int(cy)), 4)
        pygame.draw.circle(surface, (255, 255, 255), (int(cx), int(cy)), 2)