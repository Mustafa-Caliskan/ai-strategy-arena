"""
resources.py — Catan + Endless Legend Çoklu Kaynak Modeli
Gold, Food, Wood, Stone, Iron, Influence, Population, Military, Territory, Technology
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Resources:
    """Bir AI ülkesinin tüm kaynakları."""
    gold: float = 500.0
    food: float = 400.0
    wood: float = 150.0
    stone: float = 100.0
    iron: float = 50.0
    influence: float = 50.0
    population: int = 150
    army: int = 80
    territory: int = 0       # tile sayısı (haritadan güncellenir)
    technology: int = 1       # 1..10 arası seviye

    # Sabit limitler
    MAX_TECHNOLOGY: int = field(default=10, repr=False, compare=False)
    MAX_ARMY_PER_POP: float = field(default=0.8, repr=False, compare=False)

    def max_army(self) -> int:
        return int(self.population * self.MAX_ARMY_PER_POP)

    def army_food_cost(self) -> float:
        """Her tur ordu gıda tüketimi."""
        return self.army * 0.5

    def tax_income(self) -> float:
        """Her tur altın üretimi."""
        base = self.population * 0.8
        tech_mult = 1.0 + (self.technology - 1) * 0.08
        return base * tech_mult

    def food_production(self) -> float:
        """Her tur temel gıda üretimi (binalar ayrıca ekler)."""
        base = self.population * 1.2
        tech_mult = 1.0 + (self.technology - 1) * 0.05
        return base * tech_mult

    def base_influence_gain(self) -> float:
        """Her tur temel influence (nüfuz) artışı."""
        return 5.0 + (self.technology * 1.5)

    def population_growth(self) -> int:
        """Her tur nüfus artışı."""
        if self.food > self.food_per_turn_needed():
            return max(1, int(self.population * 0.02))
        elif self.food < 0:
            return -max(1, int(self.population * 0.03))
        return 0

    def food_per_turn_needed(self) -> float:
        return self.population * 0.5

    def is_starving(self) -> bool:
        return self.food <= 0

    def army_upkeep_gold(self) -> float:
        """Ordunun altın bakımı."""
        return self.army * 0.3

    def is_eliminated(self) -> bool:
        return self.population <= 0 or self.territory <= 0

    def to_dict(self) -> dict:
        return {
            "gold": round(self.gold, 1),
            "food": round(self.food, 1),
            "wood": round(self.wood, 1),
            "stone": round(self.stone, 1),
            "iron": round(self.iron, 1),
            "influence": round(self.influence, 1),
            "population": self.population,
            "army": self.army,
            "territory": self.territory,
            "technology": self.technology,
        }

    def clone(self) -> "Resources":
        return Resources(
            gold=self.gold,
            food=self.food,
            wood=self.wood,
            stone=self.stone,
            iron=self.iron,
            influence=self.influence,
            population=self.population,
            army=self.army,
            territory=self.territory,
            technology=self.technology,
        )
