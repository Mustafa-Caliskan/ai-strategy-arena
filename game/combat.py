"""
combat.py — Savaş sistemi
Attacker vs Defender, terrain bonusu, kontrollü rastgelelik.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game.country import Country
    from game.map import GameMap, Tile


@dataclass
class CombatResult:
    attacker_id: str
    defender_id: str
    attacker_won: bool
    attacker_losses: int
    defender_losses: int
    territory_captured: int
    events: list[str]
    territory_tiles: list[tuple[int, int]]   # Ele geçirilen tile koordinatları


class CombatSystem:
    """
    Savaş hesaplama motoru.
    Güç oranı + terrain + technology + randomness ile sonuç belirlenir.
    """

    # Rastgelelik katsayısı: 0 = deterministik, 1 = tam rastgele
    RANDOMNESS_FACTOR = 0.25

    def resolve_attack(
        self,
        attacker: "Country",
        defender: "Country",
        game_map: "GameMap",
        rng: Optional[random.Random] = None,
    ) -> CombatResult:
        """
        Bir ATTACK kararını çöz.
        Sonuç: kazanan, kayıplar, ele geçirilen toprak.
        """
        if rng is None:
            rng = random.Random()

        events: list[str] = []
        ra = attacker.resources
        rd = defender.resources

        # 1. Güç hesaplama
        att_power = self._calculate_attack_power(attacker, game_map)
        def_power = self._calculate_defense_power(defender, game_map)

        events.append(
            f"Combat: {attacker.agent_id} ({att_power:.1f}) vs "
            f"{defender.agent_id} ({def_power:.1f})"
        )

        # 2. Rastgelelik uygula
        rand_att = rng.uniform(1 - self.RANDOMNESS_FACTOR, 1 + self.RANDOMNESS_FACTOR)
        rand_def = rng.uniform(1 - self.RANDOMNESS_FACTOR, 1 + self.RANDOMNESS_FACTOR)
        eff_att = att_power * rand_att
        eff_def = def_power * rand_def

        attacker_won = eff_att > eff_def

        # 3. Kayıplar
        if attacker_won:
            # Saldırgan kazandı: daha az kayıp
            att_loss_ratio = rng.uniform(0.10, 0.25)
            def_loss_ratio = rng.uniform(0.30, 0.55)
        else:
            # Savunmacı kazandı
            att_loss_ratio = rng.uniform(0.25, 0.45)
            def_loss_ratio = rng.uniform(0.10, 0.20)

        att_losses = max(1, int(ra.army * att_loss_ratio))
        def_losses = max(1, int(rd.army * def_loss_ratio))

        ra.army = max(0, ra.army - att_losses)
        rd.army = max(0, rd.army - def_losses)

        # 4. Toprak ele geçirme
        captured_tiles: list[tuple[int, int]] = []
        territory_captured = 0

        if attacker_won:
            border_tiles = game_map.get_border_tiles(defender.agent_id)
            # Saldırgan gücüne göre kaç tile alacağı
            tiles_to_capture = max(1, min(
                len(border_tiles),
                int((eff_att / max(1, eff_def)) * 2)
            ))
            # Saldırgana en yakın tile'ları seç
            attacker_tiles = game_map.get_tiles_owned_by(attacker.agent_id)
            if attacker_tiles:
                ax = sum(t.x for t in attacker_tiles) / len(attacker_tiles)
                ay = sum(t.y for t in attacker_tiles) / len(attacker_tiles)
                border_tiles.sort(key=lambda t: abs(t.x - ax) + abs(t.y - ay))

            for tile in border_tiles[:tiles_to_capture]:
                game_map.capture_tile(tile.x, tile.y, attacker.agent_id)
                captured_tiles.append((tile.x, tile.y))
                territory_captured += 1

            events.append(
                f"{attacker.agent_id} WON! Captured {territory_captured} tiles. "
                f"Losses: {att_losses} att / {def_losses} def."
            )
        else:
            events.append(
                f"{defender.agent_id} DEFENDED! "
                f"Losses: {att_losses} att / {def_losses} def."
            )

        return CombatResult(
            attacker_id=attacker.agent_id,
            defender_id=defender.agent_id,
            attacker_won=attacker_won,
            attacker_losses=att_losses,
            defender_losses=def_losses,
            territory_captured=territory_captured,
            events=events,
            territory_tiles=captured_tiles,
        )

    def resolve_defend(self, country: "Country") -> str:
        """
        DEFEND action: Savunma güçlendir.
        Altın harca, savunma bonusu al (1 tur).
        """
        r = country.resources
        cost = 30.0
        if r.gold < cost:
            return "DEFEND action: no gold for fortification, holding position."
        r.gold -= cost
        # Savunma askeri geçici boost
        bonus_army = max(5, int(r.army * 0.10))
        r.army += bonus_army
        return f"{country.agent_id} fortified defenses (+{bonus_army} temporary soldiers)."

    def _calculate_attack_power(self, country: "Country", game_map: "GameMap") -> float:
        r = country.resources
        tech_mult = 1.0 + (r.technology - 1) * 0.12
        return r.army * tech_mult

    def _calculate_defense_power(self, country: "Country", game_map: "GameMap") -> float:
        r = country.resources
        tech_mult = 1.0 + (r.technology - 1) * 0.12
        # Savunmacı terrain bonusu: başkent ve şehirlerde avantaj
        terrain_bonus = self._get_terrain_defense_bonus(country.agent_id, game_map)
        return r.army * tech_mult * (1.0 + terrain_bonus)

    def _get_terrain_defense_bonus(self, agent_id: str, game_map: "GameMap") -> float:
        """Sınır tile'larının ortalama savunma bonusu."""
        from game.map import TileType
        border_tiles = game_map.get_border_tiles(agent_id)
        if not border_tiles:
            return 0.0
        total_bonus = sum(t.get_defense_bonus() for t in border_tiles)
        return total_bonus / len(border_tiles)

    def resolve_expand(
        self,
        country: "Country",
        game_map: "GameMap",
        rng: Optional[random.Random] = None,
    ) -> str:
        """
        EXPAND action: Yakın nötr toprağa genişle.
        """
        if rng is None:
            rng = random.Random()

        candidates = game_map.get_adjacent_unowned(country.agent_id)
        if not candidates:
            return f"{country.agent_id} EXPAND: no adjacent unclaimed territory."

        cost = 40.0
        r = country.resources
        if r.gold < cost:
            return f"{country.agent_id} EXPAND: insufficient gold ({r.gold:.0f}/{cost:.0f})."

        # En değerli tile'ı seç (mine > city > forest > land)
        from game.map import TileType
        priority = {TileType.MINE: 4, TileType.CITY: 3, TileType.FOREST: 2, TileType.LAND: 1}
        candidates.sort(key=lambda t: priority.get(t.tile_type, 0), reverse=True)

        tile = candidates[0]
        r.gold -= cost
        game_map.capture_tile(tile.x, tile.y, country.agent_id)
        return (f"{country.agent_id} expanded to ({tile.x},{tile.y}) "
                f"[{tile.tile_type.value}]. Cost: {cost:.0f} gold.")

    def resolve_unit_clash(
        self,
        army_a: Any,
        army_b: Any,
        tile: "Tile",
        tech_a: int = 1,
        tech_b: int = 1,
        game_map: Optional["GameMap"] = None,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        İki saha ordusu (ArmyEntity) arasındaki mikro çatışmayı hesaplar.
        Kayıplar doğrudan army.size üzerinden düşürülür.
        """
        if rng is None:
            rng = random.Random()

        # Güç hesaplama
        mult_a = 1.0 + (tech_a - 1) * 0.12
        mult_b = 1.0 + (tech_b - 1) * 0.12
        morale_a = getattr(army_a, "morale", 100.0) / 100.0
        morale_b = getattr(army_b, "morale", 100.0) / 100.0

        p_a = army_a.size * mult_a * morale_a
        def_bonus = tile.get_defense_bonus() if tile.owner == army_b.owner else 0.0
        p_b = army_b.size * mult_b * morale_b * (1.0 + def_bonus)

        rand_a = rng.uniform(0.85, 1.15)
        rand_b = rng.uniform(0.85, 1.15)
        eff_a = p_a * rand_a
        eff_b = p_b * rand_b

        a_won = eff_a > eff_b
        if a_won:
            loss_ratio_a = rng.uniform(0.10, 0.25)
            loss_ratio_b = rng.uniform(0.35, 0.65)
        else:
            loss_ratio_a = rng.uniform(0.30, 0.55)
            loss_ratio_b = rng.uniform(0.10, 0.20)

        losses_a = max(1, min(army_a.size, int(army_a.size * loss_ratio_a)))
        losses_b = max(1, min(army_b.size, int(army_b.size * loss_ratio_b)))

        army_a.size -= losses_a
        army_b.size -= losses_b

        tile_captured = False
        if army_b.size <= 0 and army_a.size > 0 and game_map:
            game_map.capture_tile(tile.x, tile.y, army_a.owner)
            tile_captured = True

        winner_id = army_a.owner if a_won else army_b.owner
        return {
            "winner_id": winner_id,
            "a_won": a_won,
            "losses_a": losses_a,
            "losses_b": losses_b,
            "remaining_a": army_a.size,
            "remaining_b": army_b.size,
            "tile_captured": tile_captured,
        }

    def resolve_city_siege(
        self,
        attacking_army: Any,
        defending_country: "Country",
        city_tile: "Tile",
        tech_att: int = 1,
        tech_def: int = 1,
        game_map: Optional["GameMap"] = None,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Saha ordusu ile şehir garnizonu arasındaki kuşatma savaşını hesaplar.
        """
        if rng is None:
            rng = random.Random()

        mult_att = 1.0 + (tech_att - 1) * 0.12
        mult_def = 1.0 + (tech_def - 1) * 0.12

        att_power = attacking_army.size * mult_att
        garrison_size = defending_country.garrison_army
        def_power = garrison_size * mult_def * (1.0 + city_tile.get_defense_bonus() + 0.30)

        rand_att = rng.uniform(0.85, 1.15)
        rand_def = rng.uniform(0.85, 1.15)
        eff_att = att_power * rand_att
        eff_def = def_power * rand_def

        att_won = eff_att > eff_def
        if att_won:
            loss_att = max(1, min(attacking_army.size, int(attacking_army.size * rng.uniform(0.15, 0.30))))
            loss_def = max(1, min(garrison_size, int(garrison_size * rng.uniform(0.40, 0.70))))
        else:
            loss_att = max(1, min(attacking_army.size, int(attacking_army.size * rng.uniform(0.35, 0.60))))
            loss_def = max(1, min(garrison_size, int(garrison_size * rng.uniform(0.10, 0.25))))

        attacking_army.size -= loss_att
        defending_country.garrison_army -= loss_def

        city_captured = False
        if defending_country.garrison_army <= 0 and attacking_army.size > 0:
            defending_country.garrison_army = 0
            if game_map:
                game_map.capture_tile(city_tile.x, city_tile.y, attacking_army.owner)
            city_captured = True

        return {
            "att_won": att_won,
            "loss_att": loss_att,
            "loss_def": loss_def,
            "remaining_att": attacking_army.size,
            "remaining_garrison": defending_country.garrison_army,
            "city_captured": city_captured,
        }
