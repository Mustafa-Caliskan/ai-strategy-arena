"""
map.py — Living World & Organik Taktiksel Harita Sistemi

20x20 grid üzerinde prosedürel Perlin-tarzı organik kıta, kıvrımlı nehirler,
taktiksel dağ geçitleri, orman siperleri ve doğal başkent bölgeleri üretir.
"""
from __future__ import annotations
import math
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
            TileType.FOREST:   0.30,  # Orman siperi (Cover)
            TileType.MOUNTAIN: 0.50,
            TileType.MINE:     0.10,
            TileType.CITY:     0.35,  # Şehir surları
            TileType.WATER:    0.0,
        }
        base = bonuses.get(self.tile_type, 0.0)
        if self.building and self.building.building_type == BuildingType.FORT:
            base += 0.50
        elif self.building and self.building.building_type == BuildingType.CITY:
            base += 0.30
        return base

    def get_resource_bonus(self) -> float:
        bonuses = {
            TileType.LAND:     1.0,
            TileType.FOREST:   1.3,
            TileType.MOUNTAIN: 0.5,
            TileType.MINE:     1.8,
            TileType.CITY:     1.6,
            TileType.WATER:    0.0,
        }
        return bonuses.get(self.tile_type, 1.0)


class GameMap:
    """
    20x20 Organik Prosedürel Taktik Haritası.
    Kıvrımlı kıyılar, nehir geçitleri, dağ sıraları ve doğal başkent çevreleri.
    """
    WIDTH = 20
    HEIGHT = 20

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._rng = random.Random(seed)
        self.tiles: list[list[Tile]] = []
        self._generate()

    def _generate(self) -> None:
        """Organik ve taktiksel canlı harita üret."""
        self.tiles = [[Tile(x, y, TileType.LAND) for y in range(self.HEIGHT)] for x in range(self.WIDTH)]

        # 1. Organik Kıyı Suları (Perlin-tarzı kavisli okyanus kenarları)
        self._generate_organic_coastlines()

        # 2. Taktik Dağ Sıraları ve Geçitler (Choke Points)
        self._generate_mountain_ridges()

        # 3. Kıvrımlı Nehir ve Doğal Köprü Geçitleri
        self._generate_river_and_bridges()

        # 4. Katmanlı Orman Kümeleri (Doğal Korular)
        self._generate_forest_groves()

        # 5. Stratejik Maden ve Nötr Köyler
        self._generate_resource_nodes()

        # 6. Başkentler ve Doğal Çevreleri (Organik dairesel başlangıç)
        self._assign_organic_territories()

    def _generate_organic_coastlines(self) -> None:
        """Harita kenarlarında doğal kavisli koylar ve kıyılar üretir."""
        for x in range(self.WIDTH):
            for y in range(self.HEIGHT):
                # Merkeze olan mesafe ve gürültü dalgası
                dist_edge = min(x, self.WIDTH - 1 - x, y, self.HEIGHT - 1 - y)
                noise = math.sin(x * 0.8 + (self.seed or 0)) * math.cos(y * 0.8)
                if dist_edge == 0 or (dist_edge == 1 and noise > 0.3):
                    self.tiles[x][y].tile_type = TileType.WATER

    def _generate_mountain_ridges(self) -> None:
        """Orta bölgelerde stratejik geçitleri olan dağ sıraları üretir."""
        # Üst ve alt dağ sırtları
        for my in [4, 15]:
            for x in range(3, self.WIDTH - 3):
                # Geçit noktaları (x=6 ve x=13 geçit olarak açık kalır)
                if x not in (6, 7, 12, 13) and self.tiles[x][my].is_passable():
                    if self._rng.random() < 0.75:
                        self.tiles[x][my].tile_type = TileType.MOUNTAIN

    def _generate_river_and_bridges(self) -> None:
        """Ortadan kıvrılarak akan taktik nehir ve 2 adet stratejik köprü."""
        mid_x = self.WIDTH // 2
        for y in range(1, self.HEIGHT - 1):
            # Hafif kavisli nehir hattı
            offset = int(math.sin(y * 0.7) * 1.5)
            rx = max(2, min(self.WIDTH - 3, mid_x + offset))
            # Köprü noktaları (y=5 ve y=14)
            if y in (5, 14):
                self.tiles[rx][y].tile_type = TileType.LAND
                self.tiles[rx][y].has_road = True
            else:
                self.tiles[rx][y].tile_type = TileType.WATER

    def _generate_forest_groves(self) -> None:
        """Doğal orman kümeleri serpiştir."""
        centers = [(4, 8), (5, 12), (15, 8), (14, 12), (10, 2), (10, 17)]
        for cx, cy in centers:
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT:
                        if self.tiles[nx][ny].tile_type == TileType.LAND and self._rng.random() < 0.7:
                            self.tiles[nx][ny].tile_type = TileType.FOREST

    def _generate_resource_nodes(self) -> None:
        """Maden ve nötr yerleşimleri yerleştir."""
        mine_spots = [(3, 6), (3, 13), (16, 6), (16, 13), (9, 7), (11, 12)]
        for mx, my in mine_spots:
            if self.tiles[mx][my].is_passable():
                self.tiles[mx][my].tile_type = TileType.MINE

        # Nötr kasabalar
        city_spots = [(9, 5), (11, 14), (6, 10), (13, 10)]
        for cx, cy in city_spots:
            if self.tiles[cx][cy].is_passable():
                self.tiles[cx][cy].tile_type = TileType.CITY
                self.tiles[cx][cy].building = Building(BuildingType.CITY, level=1)
                self.tiles[cx][cy].has_road = True

    def _assign_organic_territories(self) -> None:
        """Başkentlerin çevresinde organik dairesel etki alanları oluştur."""
        cap_a = (2, 10)
        cap_b = (17, 10)

        # AI_A Dairesel Bölgesi (Yarıçap 3.5)
        for x in range(self.WIDTH):
            for y in range(self.HEIGHT):
                if not self.tiles[x][y].is_passable():
                    continue
                dist_a = math.hypot(x - cap_a[0], y - cap_a[1])
                dist_b = math.hypot(x - cap_b[0], y - cap_b[1])

                if dist_a <= 3.8:
                    self.tiles[x][y].owner = "AI_A"
                elif dist_b <= 3.8:
                    self.tiles[x][y].owner = "AI_B"

        # Başkent binaları ve bağlantı yolları
        self.tiles[cap_a[0]][cap_a[1]].tile_type = TileType.CITY
        self.tiles[cap_a[0]][cap_a[1]].owner = "AI_A"
        self.tiles[cap_a[0]][cap_a[1]].has_road = True
        self.tiles[cap_a[0]][cap_a[1]].building = Building(BuildingType.CITY, level=2)

        self.tiles[cap_b[0]][cap_b[1]].tile_type = TileType.CITY
        self.tiles[cap_b[0]][cap_b[1]].owner = "AI_B"
        self.tiles[cap_b[0]][cap_b[1]].has_road = True
        self.tiles[cap_b[0]][cap_b[1]].building = Building(BuildingType.CITY, level=2)

    # ── Harita Sorgu Metodları ──────────────────────────────────────

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            return self.tiles[x][y]
        return None

    def get_tiles_owned_by(self, agent_id: str) -> list[Tile]:
        return [t for col in self.tiles for t in col if t.owner == agent_id]

    def get_border_tiles(self, agent_id: str) -> list[Tile]:
        """Komşusu başka bir sahip veya sahipsiz olan sınır tile'ları."""
        borders = []
        for col in self.tiles:
            for tile in col:
                if tile.owner != agent_id:
                    continue
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = self.get_tile(tile.x + dx, tile.y + dy)
                    if nb and nb.is_passable() and nb.owner != agent_id:
                        borders.append(tile)
                        break
        return borders

    def get_adjacent_unowned(self, agent_id: str) -> list[Tile]:
        """Sahipli topraklara komşu sahipsiz/nötr tile'lar."""
        unowned = []
        seen = set()
        for col in self.tiles:
            for tile in col:
                if tile.owner != agent_id:
                    continue
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = self.get_tile(tile.x + dx, tile.y + dy)
                    if nb and nb.is_passable() and nb.owner is None and (nb.x, nb.y) not in seen:
                        seen.add((nb.x, nb.y))
                        unowned.append(nb)
        return unowned

    def capture_tile(self, x: int, y: int, new_owner: str) -> bool:
        t = self.get_tile(x, y)
        if t and t.is_passable():
            t.owner = new_owner
            return True
        return False

    def build_structure(self, x: int, y: int, building_type: BuildingType, owner: Optional[str] = None) -> bool:
        t = self.get_tile(x, y)
        if not t or (owner and t.owner != owner) or t.building is not None:
            return False
        t.building = Building(building_type, level=1)
        return True

    def upgrade_structure(self, x: int, y: int, owner: Optional[str] = None) -> bool:
        t = self.get_tile(x, y)
        if not t or (owner and t.owner != owner) or not t.building:
            return False
        return t.building.upgrade()

    def get_territory_count(self, agent_id: str) -> int:
        """Belirtilen ülkenin sahip olduğu toplam tile sayısı."""
        return sum(1 for col in self.tiles for t in col if t.owner == agent_id)

    def get_nearby_resources(self, agent_id: str) -> dict:
        """Sınırlarına yakın sahipsiz/nötr kaynak sayıları."""
        nearby = {"mines": 0, "forests": 0, "cities": 0}
        for tile in self.get_adjacent_unowned(agent_id):
            if tile.tile_type == TileType.MINE:
                nearby["mines"] += 1
            elif tile.tile_type == TileType.FOREST:
                nearby["forests"] += 1
            elif tile.tile_type == TileType.CITY:
                nearby["cities"] += 1
        return nearby

    def build_road(self, x: int, y: int, owner: Optional[str] = None) -> bool:
        t = self.get_tile(x, y)
        if not t or (owner and t.owner != owner) or t.has_road:
            return False
        t.has_road = True
        return True