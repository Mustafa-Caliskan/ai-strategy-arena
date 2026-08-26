"""
map_view.py — WorldBox Tarzı Yaşayan Harita Renderer
Canlı binalar (Çiftlik, Kereste Ocağı, Maden, Kale, Şehir, Yollar), sınırlar ve başkentler
"""
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

from game.buildings import BuildingType

if TYPE_CHECKING:
    from game.map import GameMap, TileType
    from game.country import Country

# Canlı Terrain renkleri
TILE_COLORS = {
    "land":     (175, 205, 135),
    "water":    (60,  125, 185),
    "forest":   (30,  110,  45),
    "mountain": (145, 125, 105),
    "mine":     (190, 160,  55),
    "city":     (215, 205, 175),
}

TILE_BORDER = {
    "land":     (155, 185, 115),
    "water":    (45,  105, 165),
    "forest":   (18,   85,  30),
    "mountain": (115,  95,  75),
    "mine":     (170, 140,  35),
    "city":     (185, 175, 145),
}


class MapView:
    """WorldBox tarzı yaşayan 2D haritayı çizer."""

    TILE_SIZE = 36
    BORDER_WIDTH = 1

    def __init__(self, map_width: int = 20, map_height: int = 20):
        self.map_width = map_width
        self.map_height = map_height
        self.tile_size = self.TILE_SIZE
        self.surface_width  = map_width  * self.tile_size
        self.surface_height = map_height * self.tile_size

    def draw(
        self,
        surface: pygame.Surface,
        game_map: "GameMap",
        countries: list["Country"],
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Tüm haritayı verilen yüzeye çiz."""
        country_colors = {c.agent_id: c.color for c in countries}

        # 1. Zemin ve arazi
        for col in game_map.tiles:
            for tile in col:
                self._draw_tile(surface, tile, country_colors, offset_x, offset_y)

        # 2. Yollar (altyapı ağı)
        self._draw_roads(surface, game_map, offset_x, offset_y)

        # 3. Binalar ve yapılar (WorldBox binaları)
        for col in game_map.tiles:
            for tile in col:
                if tile.building:
                    self._draw_building(surface, tile, offset_x, offset_y)

        # 4. Sınır çizgileri
        self._draw_borders(surface, game_map, country_colors, offset_x, offset_y)

        # 5. Başkentler ve sancaklar
        for country in countries:
            if country.is_active():
                self._draw_capital(surface, country, offset_x, offset_y)

    def _draw_tile(self, surface, tile, country_colors, ox, oy):
        from game.map import TileType
        x = ox + tile.x * self.tile_size
        y = oy + tile.y * self.tile_size
        w = h = self.tile_size

        base_color = TILE_COLORS.get(tile.tile_type.value, (180, 180, 180))
        pygame.draw.rect(surface, base_color, (x, y, w, h))

        # Ülke sahipliği (yumuşak renk karışımı)
        if tile.owner and tile.owner in country_colors:
            owner_color = country_colors[tile.owner]
            blended = (
                int(base_color[0] * 0.60 + owner_color[0] * 0.40),
                int(base_color[1] * 0.60 + owner_color[1] * 0.40),
                int(base_color[2] * 0.60 + owner_color[2] * 0.40),
            )
            pygame.draw.rect(surface, blended, (x, y, w, h))

        # Doğal arazi detayları
        self._draw_terrain_detail(surface, tile, x, y, w, h)

        border_color = TILE_BORDER.get(tile.tile_type.value, (100, 100, 100))
        pygame.draw.rect(surface, border_color, (x, y, w, h), self.BORDER_WIDTH)

    def _draw_terrain_detail(self, surface, tile, x, y, w, h):
        from game.map import TileType
        cx, cy = x + w // 2, y + h // 2

        if tile.tile_type == TileType.FOREST and not tile.building:
            # Üçlü ağaç grubu
            pygame.draw.polygon(surface, (15, 75, 25), [(cx, cy - 8), (cx - 6, cy + 4), (cx + 6, cy + 4)])
            pygame.draw.polygon(surface, (20, 95, 35), [(cx - 6, cy - 4), (cx - 11, cy + 6), (cx - 1, cy + 6)])
            pygame.draw.polygon(surface, (20, 95, 35), [(cx + 6, cy - 4), (cx + 1, cy + 6), (cx + 11, cy + 6)])
        elif tile.tile_type == TileType.MOUNTAIN and not tile.building:
            # Çift karlı dağ tepesi
            pygame.draw.polygon(surface, (95, 80, 70), [(cx, cy - 10), (cx - 10, cy + 8), (cx + 10, cy + 8)])
            pygame.draw.polygon(surface, (240, 240, 250), [(cx, cy - 10), (cx - 4, cy - 4), (cx + 4, cy - 4)])
        elif tile.tile_type == TileType.MINE and not tile.building:
            # Doğal altın/demir damarı
            pygame.draw.circle(surface, (210, 170, 40), (cx - 4, cy), 4)
            pygame.draw.circle(surface, (160, 160, 180), (cx + 4, cy + 2), 3)
        elif tile.tile_type == TileType.WATER:
            pygame.draw.line(surface, (120, 180, 230), (x + 5, cy - 2), (x + w - 5, cy - 2), 2)
            pygame.draw.line(surface, (90, 150, 210), (x + 8, cy + 4), (x + w - 8, cy + 4), 2)

    def _draw_roads(self, surface, game_map, ox, oy):
        """Yol ağını bağlayarak çiz."""
        ts = self.tile_size
        road_color = (160, 130, 90)
        for col in game_map.tiles:
            for tile in col:
                if not tile.has_road:
                    continue
                cx = ox + tile.x * ts + ts // 2
                cy = oy + tile.y * ts + ts // 2
                pygame.draw.circle(surface, road_color, (cx, cy), 3)

                # Sağ komşu yol
                right = game_map.get_tile(tile.x + 1, tile.y)
                if right and right.has_road:
                    pygame.draw.line(surface, road_color, (cx, cy), (cx + ts, cy), 3)
                # Alt komşu yol
                below = game_map.get_tile(tile.x, tile.y + 1)
                if below and below.has_road:
                    pygame.draw.line(surface, road_color, (cx, cy), (cx, cy + ts), 3)

    def _draw_building(self, surface, tile, ox, oy):
        """WorldBox binalarını çiz."""
        ts = self.tile_size
        cx = ox + tile.x * ts + ts // 2
        cy = oy + tile.y * ts + ts // 2
        b = tile.building
        btype = b.building_type

        if btype == BuildingType.FARM:
            # Buğday tarlası (altın sarısı çizgiler ve çiftlik evi)
            pygame.draw.rect(surface, (220, 190, 60), (cx - 10, cy - 8, 20, 16), border_radius=2)
            for i in range(-8, 9, 4):
                pygame.draw.line(surface, (180, 140, 20), (cx + i, cy - 6), (cx + i, cy + 6), 2)
            pygame.draw.rect(surface, (140, 60, 40), (cx - 4, cy - 4, 8, 8))
        elif btype == BuildingType.LUMBER_MILL:
            # Kereste ocağı (kütük yığınları ve testere)
            pygame.draw.rect(surface, (110, 70, 30), (cx - 9, cy - 6, 18, 12), border_radius=2)
            pygame.draw.circle(surface, (200, 200, 210), (cx, cy), 4)
            pygame.draw.circle(surface, (60, 40, 20), (cx, cy), 2)
        elif btype == BuildingType.MINE:
            # Maden ocağı (maden girişi ve vagon)
            pygame.draw.polygon(surface, (80, 70, 60), [(cx - 9, cy + 7), (cx, cy - 7), (cx + 9, cy + 7)])
            pygame.draw.rect(surface, (30, 25, 20), (cx - 4, cy, 8, 7))
        elif btype == BuildingType.FORT:
            # Taş kale burcu ve mazgallar
            pygame.draw.rect(surface, (120, 120, 130), (cx - 9, cy - 7, 18, 14), border_radius=2)
            pygame.draw.rect(surface, (80, 80, 90), (cx - 9, cy - 10, 4, 4))
            pygame.draw.rect(surface, (80, 80, 90), (cx - 2, cy - 10, 4, 4))
            pygame.draw.rect(surface, (80, 80, 90), (cx + 5, cy - 10, 4, 4))
            pygame.draw.rect(surface, (180, 40, 40), (cx + 2, cy - 14, 5, 4))
        elif btype == BuildingType.CITY:
            # Şehir evleri ve kulesi
            pygame.draw.rect(surface, (170, 150, 130), (cx - 10, cy - 4, 20, 11))
            pygame.draw.polygon(surface, (180, 60, 40), [(cx - 11, cy - 4), (cx - 1, cy - 11), (cx + 1, cy - 4)])
            pygame.draw.polygon(surface, (180, 60, 40), [(cx - 1, cy - 4), (cx + 9, cy - 11), (cx + 11, cy - 4)])

    def _draw_borders(self, surface, game_map, country_colors, ox, oy):
        ts = self.tile_size
        for col in game_map.tiles:
            for tile in col:
                if not tile.owner:
                    continue
                tx = ox + tile.x * ts
                ty = oy + tile.y * ts
                border_col = country_colors.get(tile.owner, (255, 255, 255))
                right = game_map.get_tile(tile.x + 1, tile.y)
                if right and right.owner != tile.owner:
                    pygame.draw.line(surface, border_col, (tx + ts, ty), (tx + ts, ty + ts), 2)
                below = game_map.get_tile(tile.x, tile.y + 1)
                if below and below.owner != tile.owner:
                    pygame.draw.line(surface, border_col, (tx, ty + ts), (tx + ts, ty + ts), 2)

    def _draw_capital(self, surface, country, ox, oy):
        cx = ox + country.capital_x * self.tile_size + self.tile_size // 2
        cy = oy + country.capital_y * self.tile_size + self.tile_size // 2
        r = country.color
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 9)
        pygame.draw.circle(surface, r, (cx, cy), 7)
        pygame.draw.circle(surface, (255, 215, 0), (cx, cy), 3)
