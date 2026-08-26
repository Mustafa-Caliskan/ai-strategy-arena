"""
map.py — Living World Harita Sistemi
20x20 grid, tile tipleri, yapılar (binalar), yollar, simetrik başlangıç
"""
from __future__ import annotations
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from game.buildings import Building, BuildingType, BUILDING_COSTS


class TileType(Enum):
    LAND = "land"
    WATER = "water"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    MINE = "mine"
    CITY = "city"


@dataclass
class Tile:
    x: int
    y: int
    tile_type: TileType
    owner: Optional[str] = None          # AI id veya None
    resource_bonus: float = 0.0           # Üretim çarpanı
    defense_bonus: float = 0.0            # Savunma çarpanı
    has_army: bool = False
    building: Optional[Building] = None   # Tile üzerindeki yapı
    has_road: bool = False                # Bağlantı yolu var mı

    def is_passable(self) -> bool:
        return self.tile_type not in (TileType.WATER, TileType.MOUNTAIN)

    def get_defense_bonus(self) -> float:
        bonuses = {
            TileType.LAND:     0.0,
            TileType.FOREST:   0.15,
            TileType.MOUNTAIN: 0.35,
            TileType.MINE:     0.05,
            TileType.CITY:     0.20,
            TileType.WATER:    0.0,
        }
        base = bonuses.get(self.tile_type, 0.0)
        # Kale veya bina bonusu ekle
        if self.building and self.building.building_type == BuildingType.FORT:
            base += 0.40
        elif self.building and self.building.building_type == BuildingType.CITY:
            base += 0.25
        return base

    def get_resource_bonus(self) -> float:
        bonuses = {
            TileType.LAND:     1.0,
            TileType.FOREST:   1.2,
            TileType.MOUNTAIN: 0.6,
            TileType.MINE:     1.6,
            TileType.CITY:     1.5,
            TileType.WATER:    0.0,
        }
        return bonuses.get(self.tile_type, 1.0)


class GameMap:
    """
    20x20 grid yaşayan harita.
    Sol yarı AI_A, sağ yarı AI_B başlangıç bölgesi.
    """
    WIDTH = 20
    HEIGHT = 20

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._rng = random.Random(seed)
        self.tiles: list[list[Tile]] = []
        self._generate()

    def _generate(self) -> None:
        """Simetrik ama canlı harita üret."""
        self.tiles = [[Tile(x, y, TileType.LAND)
                       for y in range(self.HEIGHT)]
                      for x in range(self.WIDTH)]

        self._place_water_edges()
        self._place_terrain(TileType.FOREST, count=24)
        self._place_terrain(TileType.MOUNTAIN, count=14)
        self._place_terrain(TileType.MINE, count=8)
        self._place_neutral_cities()
        self._assign_starting_territories()

    def _place_water_edges(self) -> None:
        """Haritanın üst ve alt kenarına su koy."""
        for x in range(self.WIDTH):
            self.tiles[x][0].tile_type = TileType.WATER
            self.tiles[x][self.HEIGHT - 1].tile_type = TileType.WATER

    def _place_terrain(self, tile_type: TileType, count: int) -> None:
        """Belirli terrain tipini rastgele ama dengeli yerleştir."""
        placed = 0
        attempts = 0
        while placed < count and attempts < 500:
            attempts += 1
            x = self._rng.randint(1, self.WIDTH - 2)
            y = self._rng.randint(1, self.HEIGHT - 2)
            tile = self.tiles[x][y]
            if tile.tile_type == TileType.LAND:
                if x in range(1, 4) or x in range(16, 19):
                    if tile_type in (TileType.MOUNTAIN, TileType.WATER):
                        continue
                tile.tile_type = tile_type
                placed += 1

    def _place_neutral_cities(self) -> None:
        """Orta bölgeye nötr şehirler koy (x=7..12)."""
        city_positions = [
            (7, 5), (7, 14), (10, 10), (12, 5), (12, 14)
        ]
        for x, y in city_positions:
            if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
                t = self.tiles[x][y]
                t.tile_type = TileType.CITY
                t.building = Building(BuildingType.CITY)

    def _assign_starting_territories(self) -> None:
        """AI başlangıç şehirlerini, topraklarını ve temel binalarını belirle."""
        # AI_A Başkenti
        self.tiles[2][10].tile_type = TileType.CITY
        self.tiles[2][10].owner = "AI_A"
        self.tiles[2][10].building = Building(BuildingType.CITY, level=1)
        self.tiles[2][10].has_road = True

        # AI_B Başkenti
        self.tiles[17][10].tile_type = TileType.CITY
        self.tiles[17][10].owner = "AI_B"
        self.tiles[17][10].building = Building(BuildingType.CITY, level=1)
        self.tiles[17][10].has_road = True

        # AI_A başlangıç toprağı: x=0..4
        for x in range(0, 5):
            for y in range(1, self.HEIGHT - 1):
                t = self.tiles[x][y]
                if t.tile_type not in (TileType.WATER, TileType.MOUNTAIN):
                    t.owner = "AI_A"
        # Başlangıç çiftlikleri ve kereste ocakları
        self.tiles[2][9].building = Building(BuildingType.FARM)
        self.tiles[2][11].building = Building(BuildingType.LUMBER_MILL)
        self.tiles[2][9].has_road = True
        self.tiles[2][11].has_road = True

        # AI_B başlangıç toprağı: x=15..19
        for x in range(15, self.WIDTH):
            for y in range(1, self.HEIGHT - 1):
                t = self.tiles[x][y]
                if t.tile_type not in (TileType.WATER, TileType.MOUNTAIN):
                    t.owner = "AI_B"
        self.tiles[17][9].building = Building(BuildingType.FARM)
        self.tiles[17][11].building = Building(BuildingType.LUMBER_MILL)
        self.tiles[17][9].has_road = True
        self.tiles[17][11].has_road = True

    # ── Sorgulama ve İnşaat ───────────────────────────────────────────

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            return self.tiles[x][y]
        return None

    def get_tiles_owned_by(self, agent_id: str) -> list[Tile]:
        result = []
        for col in self.tiles:
            for tile in col:
                if tile.owner == agent_id:
                    result.append(tile)
        return result

    def get_territory_count(self, agent_id: str) -> int:
        return len(self.get_tiles_owned_by(agent_id))

    def get_border_tiles(self, agent_id: str) -> list[Tile]:
        owned = set()
        for col in self.tiles:
            for t in col:
                if t.owner == agent_id:
                    owned.add((t.x, t.y))

        borders = []
        for (x, y) in owned:
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT:
                    neighbor = self.tiles[nx][ny]
                    if neighbor.owner != agent_id:
                        borders.append(self.tiles[x][y])
                        break
        return borders

    def get_adjacent_unowned(self, agent_id: str) -> list[Tile]:
        owned = set()
        for col in self.tiles:
            for t in col:
                if t.owner == agent_id:
                    owned.add((t.x, t.y))

        candidates = []
        seen = set()
        for (x, y) in owned:
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if (nx, ny) in seen:
                    continue
                if 0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT:
                    t = self.tiles[nx][ny]
                    if t.owner is None and t.is_passable():
                        candidates.append(t)
                        seen.add((nx, ny))
        return candidates

    def build_structure(self, x: int, y: int, building_type: BuildingType) -> bool:
        """Tile üzerine yapı inşa et."""
        tile = self.get_tile(x, y)
        if not tile or not tile.is_passable():
            return False
        if building_type == BuildingType.ROAD:
            tile.has_road = True
            return True
        tile.building = Building(building_type)
        if building_type == BuildingType.CITY:
            tile.tile_type = TileType.CITY
        return True

    def capture_tile(self, x: int, y: int, new_owner: str) -> bool:
        tile = self.get_tile(x, y)
        if tile and tile.is_passable():
            tile.owner = new_owner
            return True
        return False

    def get_nearby_resources(self, agent_id: str) -> list[str]:
        owned = self.get_tiles_owned_by(agent_id)
        resources = []
        seen = set()
        for t in owned:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    nx, ny = t.x + dx, t.y + dy
                    if (nx, ny) in seen:
                        continue
                    seen.add((nx, ny))
                    neighbor = self.get_tile(nx, ny)
                    if neighbor and neighbor.tile_type in (TileType.MINE, TileType.CITY, TileType.FOREST):
                        resources.append(neighbor.tile_type.value)
        return list(set(resources))
