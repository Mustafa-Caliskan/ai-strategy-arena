"""
combat.py — Taktiksel Savaş ve Yetenek Sistemi (Tactical Combat Engine)

- 4 Asker Sınıfı Arasında Taktiksel Çatışma (Piyade, Okçu, Süvari, Mancınık)
- Uzak Menzil Saldırıları (Ranged Attack - Hasar almadan vurma)
- Yakın Dövüş ve Karşı Saldırı (Melee Clash & Counter-attack)
- Arazi Siper Bonusu (Orman: %30 Siper, Tepe: %25 Menzil & Hasar Bonusu)
- Özel Yetenekler (Kalkan Duvarı, Ateş Oku, Süvari Hücumu, Kuşatma Bombardımanı)
- Can (HP) ve Asker Sayısı Kayıp Hesaplaması
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Any

from game.entities import UnitClass, ArmyEntity, ArmyStatus

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
    territory_tiles: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class TacticalAttackResult:
    attacker_id: str
    target_id: str
    damage_dealt: float
    retaliation_damage: float
    is_ranged: bool
    target_killed: bool
    attacker_killed: bool
    is_critical: bool
    events: list[str]


class CombatSystem:
    """Taktiksel savaş ve yetenek hesaplama motoru."""

    RANDOMNESS_FACTOR = 0.20

    # ── Taktiksel Birlik Saldırısı (Unit vs Unit) ───────────────────

    def resolve_tactical_attack(
        self,
        attacker: ArmyEntity,
        target: ArmyEntity,
        game_map: "GameMap",
        rng: Optional[random.Random] = None,
    ) -> TacticalAttackResult:
        """
        İki taktiksel birlik arasındaki çatışmayı çözer.
        Menzilli ise misillemesiz uzaktan vurur; yakın dövüş ise karşılıklı vuruşur.
        """
        if rng is None:
            rng = random.Random()

        events = []
        dist = math.hypot(attacker.x - target.x, attacker.y - target.y)
        is_ranged = (dist > 1.4)
        target_tile = game_map.get_tile(target.x, target.y)
        attacker_tile = game_map.get_tile(attacker.x, attacker.y)

        # 1. Saldırı Gücü Hesaplama
        base_atk = attacker.attack_power * (attacker.hp / max(1.0, attacker.max_hp))
        rand_mult = rng.uniform(0.85, 1.15)
        is_critical = (rng.random() < 0.15)
        crit_mult = 1.4 if is_critical else 1.0

        # Süvari Hücum Bonusu
        if attacker.unit_class == UnitClass.CAVALRY and not is_ranged:
            base_atk *= 1.35
            events.append(f"🐎 [CHARGE] {attacker.id} executed a cavalry charge!")

        raw_dmg = base_atk * rand_mult * crit_mult

        # 2. Savunma ve Siper İndirimi
        target_def = target.defense_power
        if target.is_fortified:
            target_def *= 1.50
            events.append(f"🛡️ [SHIELD_WALL] {target.id} reduced damage behind shield wall!")

        # Orman Siperi (Cover against ranged)
        cover_mult = 1.0
        if is_ranged and target_tile and target_tile.tile_type.value == "forest":
            cover_mult = 0.70
            events.append(f"🌲 [COVER] {target.id} took cover inside the dense forest!")

        # Net Hasar
        dmg_dealt = max(5.0, (raw_dmg - target_def * 0.5) * cover_mult)
        actual_dealt = target.take_damage(dmg_dealt)

        events.append(
            f"⚔️ {attacker.id} ({attacker.unit_class.value.upper()}) attacked {target.id} "
            f"for {actual_dealt:.1f} HP! {'(CRITICAL!)' if is_critical else ''}"
        )

        # 3. Misilleme (Yalnızca yakın dövüşte ve hedef hayattaysa)
        retal_dmg = 0.0
        if not is_ranged and target.is_alive():
            retal_raw = target.attack_power * (target.hp / max(1.0, target.max_hp)) * rng.uniform(0.70, 0.90)
            retal_dmg = max(2.0, retal_raw - attacker.defense_power * 0.4)
            attacker.take_damage(retal_dmg)
            events.append(f"↩️ {target.id} retaliated for {retal_dmg:.1f} damage!")

        target_killed = not target.is_alive()
        attacker_killed = not attacker.is_alive()

        if target_killed:
            events.append(f"💀 [DEFEAT] {target.id} was eliminated!")
            # Hedefin bulunduğu kareyi ele geçir
            if target_tile:
                game_map.capture_tile(target.x, target.y, attacker.owner)

        if attacker_killed:
            events.append(f"💀 [DEFEAT] {attacker.id} was eliminated in counter-attack!")

        return TacticalAttackResult(
            attacker_id=attacker.id,
            target_id=target.id,
            damage_dealt=actual_dealt,
            retaliation_damage=retal_dmg,
            is_ranged=is_ranged,
            target_killed=target_killed,
            attacker_killed=attacker_killed,
            is_critical=is_critical,
            events=events,
        )

    # ── Geriye Dönük Uyumluluk (Macro Turn Çözümleri) ───────────────

    def resolve_attack(
        self,
        attacker: "Country",
        defender: "Country",
        game_map: "GameMap",
        rng: Optional[random.Random] = None,
    ) -> CombatResult:
        """Makro ATTACK kararı çözümü."""
        if rng is None:
            rng = random.Random()

        events: list[str] = []
        ra = attacker.resources
        rd = defender.resources

        att_power = ra.army * (1.0 + (ra.technology - 1) * 0.12)
        def_power = rd.army * (1.0 + (rd.technology - 1) * 0.12) * (1.0 + self._get_terrain_defense_bonus(defender.agent_id, game_map))

        eff_att = att_power * rng.uniform(0.85, 1.15)
        eff_def = def_power * rng.uniform(0.85, 1.15)

        attacker_won = eff_att > eff_def
        if attacker_won:
            att_loss_ratio = rng.uniform(0.10, 0.20)
            def_loss_ratio = rng.uniform(0.30, 0.50)
        else:
            att_loss_ratio = rng.uniform(0.25, 0.40)
            def_loss_ratio = rng.uniform(0.10, 0.20)

        att_losses = max(1, int(ra.army * att_loss_ratio))
        def_losses = max(1, int(rd.army * def_loss_ratio))

        ra.army = max(0, ra.army - att_losses)
        rd.army = max(0, rd.army - def_losses)

        captured_tiles: list[tuple[int, int]] = []
        territory_captured = 0

        if attacker_won:
            border_tiles = game_map.get_border_tiles(defender.agent_id)
            tiles_to_capture = max(1, min(len(border_tiles), int((eff_att / max(1, eff_def)) * 2)))
            for tile in border_tiles[:tiles_to_capture]:
                game_map.capture_tile(tile.x, tile.y, attacker.agent_id)
                captured_tiles.append((tile.x, tile.y))
                territory_captured += 1

            events.append(f"{attacker.agent_id} WON! Captured {territory_captured} tiles. Losses: {att_losses} att / {def_losses} def.")
        else:
            events.append(f"{defender.agent_id} DEFENDED! Losses: {att_losses} att / {def_losses} def.")

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
        r = country.resources
        cost = 30.0
        if r.gold < cost:
            return "DEFEND action: no gold for fortification, holding position."
        r.gold -= cost
        bonus_army = max(5, int(r.army * 0.10))
        r.army += bonus_army
        return f"{country.agent_id} fortified defenses (+{bonus_army} temporary soldiers)."

    def resolve_expand(
        self,
        country: "Country",
        game_map: "GameMap",
        rng: Optional[random.Random] = None,
    ) -> str:
        candidates = game_map.get_adjacent_unowned(country.agent_id)
        if not candidates:
            return f"{country.agent_id} EXPAND: no adjacent unclaimed territory."

        cost = 40.0
        r = country.resources
        if r.gold < cost:
            return f"{country.agent_id} EXPAND: insufficient gold ({r.gold:.0f}/{cost:.0f})."

        from game.map import TileType
        priority = {TileType.MINE: 4, TileType.CITY: 3, TileType.FOREST: 2, TileType.LAND: 1}
        candidates.sort(key=lambda t: priority.get(t.tile_type, 0), reverse=True)

        tile = candidates[0]
        r.gold -= cost
        game_map.capture_tile(tile.x, tile.y, country.agent_id)
        return f"{country.agent_id} expanded to ({tile.x},{tile.y}) [{tile.tile_type.value}]. Cost: {cost:.0f} gold."

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
        """Saha orduları çatışması (Entity vs Entity)."""
        res = self.resolve_tactical_attack(army_a, army_b, game_map, rng)
        return {
            "winner": army_a.owner if res.target_killed else (army_b.owner if res.attacker_killed else "draw"),
            "losses_a": int(res.retaliation_damage),
            "losses_b": int(res.damage_dealt),
            "events": res.events,
            "tile_captured": res.target_killed,
        }

    def _get_terrain_defense_bonus(self, agent_id: str, game_map: "GameMap") -> float:
        border_tiles = game_map.get_border_tiles(agent_id)
        if not border_tiles:
            return 0.0
        return sum(t.get_defense_bonus() for t in border_tiles) / len(border_tiles)