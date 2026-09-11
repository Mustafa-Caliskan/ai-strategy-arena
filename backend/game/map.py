"""
backend/game/map.py
Odd-R 3 Oyunculu Fantezi Harita Motoru v3.0
OpenAI (Kuzey), DeepSeek (Güneydoğu) ve Claude (Güneybatı) Üç Kutup Düzeni.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple


class TerrainType(str, Enum):
    PLAINS       = "plains"        # Zümrüt Çayır / Ova
    FOREST       = "forest"        # Yoğun Ulu Orman
    MOUNTAIN     = "mountain"      # Karlı Dağ Silsilesi
    WATER        = "water"         # Derin Okyanus / İç Deniz
    BRIDGE       = "bridge"        # Kadim Taş Köprü
    KEEP_1       = "keep_1"        # OpenAI İmparatorluk Başkenti (Kuzey)
    KEEP_2       = "keep_2"        # DeepSeek Orman Başkenti (Güneydoğu)
    KEEP_3       = "keep_3"        # Claude Mistik Bilge Kalesi (Güneybatı)
    RELIC_ISLAND = "relic_island"  # Merkez Kadim Büyü Adası (+15g/tur)
    BARBARIAN    = "barbarian"     # Vahşi Barbar Köyü


@dataclass
class HexTile:
    col: int       # Odd-R column
    row: int       # Odd-R row
    terrain: TerrainType = TerrainType.PLAINS
    owner_id: int = 0             # 0=Tarafsız, 1=OpenAI, 2=DeepSeek, 3=Claude, 4=Barbar
    building: Optional[str] = None
    unit_id: Optional[str] = None


class ArenaMap:
    def __init__(self, cols: int = 28, rows: int = 18):
        self.cols = cols
        self.rows = rows
        self.tiles: Dict[Tuple[int, int], HexTile] = {}
        self.generate_world()

    def generate_world(self):
        """3 Krallığın merkez adaya eşit mesafede olduğu estetik kıta haritası."""
        for r in range(self.rows):
            for c in range(self.cols):
                terrain = TerrainType.PLAINS
                owner = 0

                # 1. Doğu Ticaret Denizi (c >= 25)
                if c >= 25:
                    terrain = TerrainType.WATER

                # 2. İç Deniz ve Merkez Ada
                # Merkez Ada: col 12..15, row 8..10
                elif 12 <= c <= 15 and 8 <= r <= 10:
                    terrain = TerrainType.RELIC_ISLAND

                # İç Deniz Halkası (Merkez Adayı kuşatır)
                elif 8 <= c <= 19 and 6 <= r <= 12:
                    # 3 Taraflı Köprü Ağı
                    # Kuzey Köprüsü (OpenAI -> Merkez)
                    if c in (13, 14) and r in (6, 7):
                        terrain = TerrainType.BRIDGE
                    # Güneydoğu Köprüsü (DeepSeek -> Merkez)
                    elif (c, r) in [(17, 11), (18, 12)]:
                        terrain = TerrainType.BRIDGE
                    # Güneybatı Köprüsü (Claude -> Merkez)
                    elif (c, r) in [(10, 11), (9, 12)]:
                        terrain = TerrainType.BRIDGE
                    else:
                        terrain = TerrainType.WATER

                # 3. Vahşi Barbar Toprakları (Tampon Bölgeler)
                elif (c, r) in [(2, 2), (2, 8), (13, 17), (25, 6), (24, 16)]:
                    terrain = TerrainType.BARBARIAN
                    owner = 4

                # 4. Doğal Dağ Kuşakları ve Ormanlar
                elif (c in (7, 8) and r in (2, 3, 4)) or (c in (19, 20) and r in (2, 3, 4)) or (c in (13, 14) and r == 14):
                    terrain = TerrainType.MOUNTAIN
                elif (c * 5 + r * 7) % 6 == 0:
                    terrain = TerrainType.FOREST

                self.tiles[(c, r)] = HexTile(col=c, row=r, terrain=terrain, owner_id=owner)

        # 5. ÜÇ BAŞKENT HİSARI (CITADELS)
        # Kuzey: OpenAI (13, 2)
        self.tiles[(13, 2)].terrain = TerrainType.KEEP_1
        self.tiles[(13, 2)].owner_id = 1
        self.tiles[(14, 2)].owner_id = 1

        # Güneydoğu: DeepSeek (21, 15)
        self.tiles[(21, 15)].terrain = TerrainType.KEEP_2
        self.tiles[(21, 15)].owner_id = 2
        self.tiles[(22, 15)].owner_id = 2

        # Güneybatı: Claude (5, 15)
        self.tiles[(5, 15)].terrain = TerrainType.KEEP_3
        self.tiles[(5, 15)].owner_id = 3
        self.tiles[(6, 15)].owner_id = 3

    def get_keep_coord(self, side_id: int) -> Tuple[int, int]:
        if side_id == 1:
            return (13, 2)
        elif side_id == 2:
            return (21, 15)
        else:
            return (5, 15)

    def get_center_relic_coord(self) -> Tuple[int, int]:
        return (13, 9)

    @staticmethod
    def hex_distance(c1: int, r1: int, c2: int, r2: int) -> int:
        """Odd-R offset hex mesafesi."""
        q1 = c1 - (r1 - (r1 & 1)) // 2
        z1 = r1
        y1 = -q1 - z1

        q2 = c2 - (r2 - (r2 & 1)) // 2
        z2 = r2
        y2 = -q2 - z2

        return max(abs(q1 - q2), abs(y1 - y2), abs(z1 - z2))

    def serialize(self) -> List[dict]:
        return [
            {
                "col": tile.col,
                "row": tile.row,
                "terrain": tile.terrain.value,
                "owner": tile.owner_id,
                "building": tile.building
            }
            for tile in self.tiles.values()
        ]
