"""
economy.py — Catan + WorldBox Çoklu Kaynak ve Altyapı Ekonomi Sistemi
Kaynak üretimi (Gold, Food, Wood, Stone, Iron, Influence), tüketim, inşaat ve ordu üretimi.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.buildings import Building, BuildingType, BUILDING_COSTS, BUILDING_YIELDS

if TYPE_CHECKING:
    from game.country import Country
    from game.map import GameMap, Tile


@dataclass
class EconomyResult:
    agent_id: str
    gold_change: float
    food_change: float
    wood_change: float
    stone_change: float
    iron_change: float
    influence_change: float
    population_change: int
    is_starving: bool
    events: list[str]


class EconomySystem:
    """
    Her tur çağrılır, tüm ülkelerin çoklu kaynak ekonomisini günceller.
    """

    def process_turn(self, country: "Country", game_map: "GameMap") -> EconomyResult:
        """
        Bir ülkenin tur ekonomisini işle.
        Sıra: Bina & Harita Üretimi → Tüketim → Nüfus büyümesi
        """
        r = country.resources
        events: list[str] = []

        # 1. Temel üretimler
        gold_produced = r.tax_income()
        food_produced = r.food_production()
        wood_produced = 10.0
        stone_produced = 5.0
        iron_produced = 2.0
        influence_produced = r.base_influence_gain()

        # 2. Haritadaki binalardan ve arazilerden gelen üretimler
        map_yields = self._calculate_map_yields(country.agent_id, game_map)
        gold_produced += map_yields.get("gold", 0.0)
        food_produced += map_yields.get("food", 0.0)
        wood_produced += map_yields.get("wood", 0.0)
        stone_produced += map_yields.get("stone", 0.0)
        iron_produced += map_yields.get("iron", 0.0)
        influence_produced += map_yields.get("influence", 0.0)

        # 3. Altın tüketimi (ordu bakımı)
        gold_spent = r.army_upkeep_gold()
        gold_change = gold_produced - gold_spent

        # 4. Gıda tüketimi (nüfus + ordu)
        food_consumed = r.food_per_turn_needed() + r.army_food_cost()
        food_change = food_produced - food_consumed

        # 5. Açlık kontrolü
        is_starving = False
        if r.food + food_change < 0:
            is_starving = True
            events.append(f"{country.agent_id} is starving!")
            deserters = max(2, int(r.army * 0.05))
            r.army = max(0, r.army - deserters)
            events.append(f"{country.agent_id} lost {deserters} soldiers to starvation.")

        # 6. Nüfus değişimi
        pop_change = r.population_growth()
        if is_starving:
            pop_change = -max(1, int(r.population * 0.03))

        # 7. Kaynakları uygula
        r.gold += gold_change
        r.food = max(0.0, r.food + food_change)
        r.wood += wood_produced
        r.stone += stone_produced
        r.iron += iron_produced
        r.influence += influence_produced
        r.population = max(0, r.population + pop_change)

        if r.gold < 0:
            unable = int(abs(r.gold) / 0.3) + 1
            r.army = max(0, r.army - unable)
            r.gold = 0.0
            events.append(f"{country.agent_id} can't afford army upkeep, disbanded {unable} soldiers.")

        return EconomyResult(
            agent_id=country.agent_id,
            gold_change=round(gold_change, 1),
            food_change=round(food_change, 1),
            wood_change=round(wood_produced, 1),
            stone_change=round(stone_produced, 1),
            iron_change=round(iron_produced, 1),
            influence_change=round(influence_produced, 1),
            population_change=pop_change,
            is_starving=is_starving,
            events=events,
        )

    def _calculate_map_yields(self, agent_id: str, game_map: "GameMap") -> dict[str, float]:
        """Ülkenin sahip olduğu tile'lar ve binalardan gelen gelirler."""
        from game.map import TileType
        totals = {"gold": 0.0, "food": 0.0, "wood": 0.0, "stone": 0.0, "iron": 0.0, "influence": 0.0}

        for col in game_map.tiles:
            for tile in col:
                if tile.owner == agent_id:
                    # Doğal arazi bonusu
                    if tile.tile_type == TileType.FOREST:
                        totals["wood"] += 12.0
                        totals["food"] += 4.0
                    elif tile.tile_type == TileType.MINE:
                        totals["stone"] += 10.0
                        totals["iron"] += 6.0
                        totals["gold"] += 8.0
                    elif tile.tile_type == TileType.CITY:
                        totals["gold"] += 15.0
                        totals["influence"] += 5.0

                    # Yol bonusu
                    if tile.has_road:
                        totals["gold"] += 3.0

                    # Bina üretimi
                    if tile.building:
                        y = tile.building.get_yields()
                        for k, v in y.items():
                            if k in totals:
                                totals[k] += v

        return totals

    # ── Eylem uygulayıcıları ──────────────────────────────────────────

    def apply_build_action(
        self, country: "Country", game_map: "GameMap", building_str: str, target_coords: Optional[str] = None
    ) -> str:
        """
        BUILD action: Çiftlik, Kereste Ocağı, Maden, Kale veya Yol inşa et.
        """
        # Bina tipini tespit et
        btype_map = {
            "FARM": BuildingType.FARM,
            "LUMBER_MILL": BuildingType.LUMBER_MILL,
            "MINE": BuildingType.MINE,
            "FORT": BuildingType.FORT,
            "ROAD": BuildingType.ROAD,
            "CITY": BuildingType.CITY,
        }
        btype = btype_map.get(building_str.upper(), BuildingType.FARM)
        cost = BUILDING_COSTS[btype]
        r = country.resources

        # Kaynak kontrolü
        if r.gold < cost.gold or r.wood < cost.wood or r.stone < cost.stone or r.iron < cost.iron:
            return (f"BUILD {btype.value} failed: Insufficient resources. "
                    f"Needs: Gold {cost.gold:.0f}, Wood {cost.wood:.0f}, Stone {cost.stone:.0f}, Iron {cost.iron:.0f}")

        # İnşa edilecek uygun tile bul
        owned_tiles = game_map.get_tiles_owned_by(country.agent_id)
        if not owned_tiles:
            return f"BUILD failed: {country.agent_id} owns no territory."

        target_tile = None
        if target_coords and "," in target_coords:
            try:
                tx, ty = map(int, target_coords.split(","))
                t = game_map.get_tile(tx, ty)
                if t and t.owner == country.agent_id:
                    target_tile = t
            except Exception:
                pass

        if not target_tile:
            # Otomatik en uygun tile'ı seç
            from game.map import TileType
            if btype == BuildingType.LUMBER_MILL:
                forests = [t for t in owned_tiles if t.tile_type == TileType.FOREST and not t.building]
                target_tile = forests[0] if forests else owned_tiles[0]
            elif btype == BuildingType.MINE:
                mines = [t for t in owned_tiles if t.tile_type in (TileType.MINE, TileType.MOUNTAIN) and not t.building]
                target_tile = mines[0] if mines else owned_tiles[0]
            elif btype == BuildingType.FORT:
                borders = [t for t in game_map.get_border_tiles(country.agent_id) if not t.building]
                target_tile = borders[0] if borders else owned_tiles[0]
            else:
                empty = [t for t in owned_tiles if not t.building]
                target_tile = empty[0] if empty else owned_tiles[0]

        # Maliyeti düş
        r.gold -= cost.gold
        r.wood -= cost.wood
        r.stone -= cost.stone
        r.iron -= cost.iron

        # İnşa et
        game_map.build_structure(target_tile.x, target_tile.y, btype)
        return f"{country.agent_id} constructed {btype.value.upper()} at ({target_tile.x},{target_tile.y})."

    def apply_recruit_action(self, country: "Country", amount: int = 20) -> str:
        """
        RECRUIT action: Altın ve Demir harcayarak ordu üret.
        """
        r = country.resources
        gold_cost = amount * 2.0
        iron_cost = amount * 1.0

        if r.gold < gold_cost:
            return f"RECRUIT failed: Need {gold_cost:.0f} gold (have {r.gold:.0f})."
        if r.iron < iron_cost:
            return f"RECRUIT failed: Need {iron_cost:.0f} iron (have {r.iron:.0f})."
        if r.army + amount > r.max_army():
            return f"RECRUIT failed: Population limit reached ({r.army}/{r.max_army()})."

        r.gold -= gold_cost
        r.iron -= iron_cost
        r.army += amount
        return f"{country.agent_id} recruited {amount} armed soldiers. Total army: {r.army}."

    def apply_economy_action(self, country: "Country") -> str:
        """ECONOMY action: Çiftliklere ve temel ekonomiye yatırım yap."""
        r = country.resources
        cost = 60.0
        if r.gold < cost:
            return "ECONOMY action failed: insufficient gold."
        r.gold -= cost
        r.food += 80.0
        r.wood += 30.0
        r.population += max(2, int(r.population * 0.03))
        return f"{country.agent_id} boosted economy: +80 Food, +30 Wood, population grew."

    def apply_research_action(self, country: "Country") -> str:
        """RESEARCH action: Teknoloji seviyesini artır."""
        r = country.resources
        cost = 120.0 + r.technology * 40.0
        if r.technology >= r.MAX_TECHNOLOGY:
            return "RESEARCH action failed: already at max technology."
        if r.gold < cost:
            return f"RESEARCH action failed: need {cost:.0f} gold, have {r.gold:.0f}."
        r.gold -= cost
        r.technology += 1
        return f"Research complete! Technology level: {r.technology}."
