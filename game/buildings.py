"""
buildings.py — WorldBox tarzı altyapı ve bina sistemi
Tile üzerinde inşa edilebilen yapılar: Çiftlik, Kereste Ocağı, Maden, Kale, Yol, Şehir
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class BuildingType(Enum):
    FARM = "farm"               # +Food üretir
    LUMBER_MILL = "lumber_mill" # +Wood üretir
    MINE = "mine"               # +Stone ve +Iron üretir
    FORT = "fort"               # +Savunma bonusu (%40)
    ROAD = "road"               # Hareket ve ticaret verimliliği
    CITY = "city"               # Nüfus, Gold ve Influence üretir


@dataclass
class BuildingCost:
    gold: float = 0.0
    wood: float = 0.0
    stone: float = 0.0
    iron: float = 0.0


# Bina inşaat maliyetleri (Catan tarzı kaynak trade-off)
BUILDING_COSTS = {
    BuildingType.FARM:        BuildingCost(gold=30.0, wood=40.0, stone=10.0),
    BuildingType.LUMBER_MILL: BuildingCost(gold=30.0, wood=20.0, stone=20.0),
    BuildingType.MINE:        BuildingCost(gold=50.0, wood=50.0, stone=30.0),
    BuildingType.FORT:        BuildingCost(gold=60.0, wood=30.0, stone=70.0, iron=20.0),
    BuildingType.ROAD:        BuildingCost(gold=15.0, wood=10.0, stone=15.0),
    BuildingType.CITY:        BuildingCost(gold=150.0, wood=100.0, stone=100.0, iron=40.0),
}


# Bina üretim bonusları (Her tur başına)
BUILDING_YIELDS = {
    BuildingType.FARM:        {"food": 35.0},
    BuildingType.LUMBER_MILL: {"wood": 25.0},
    BuildingType.MINE:        {"stone": 20.0, "iron": 12.0, "gold": 10.0},
    BuildingType.FORT:        {"defense_bonus": 0.40},
    BuildingType.ROAD:        {"trade_gold": 5.0},
    BuildingType.CITY:        {"gold": 25.0, "food": 15.0, "influence": 8.0, "pop_cap": 50},
}


@dataclass
class Building:
    building_type: BuildingType
    level: int = 1
    health: float = 100.0
    turns_active: int = 0

    def get_yields(self) -> dict:
        base = BUILDING_YIELDS.get(self.building_type, {})
        mult = 1.0 + (self.level - 1) * 0.5
        return {k: (v * mult if isinstance(v, (int, float)) else v) for k, v in base.items()}
