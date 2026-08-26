"""
game_state.py — Oyun durumu ve Fog of War
Her AI için filtrelenmiş game state JSON üretimi.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game.country import Country
    from game.map import GameMap
    from game.diplomacy import DiplomacySystem


# Kullanılabilir eylemler
AVAILABLE_ACTIONS = [
    "ATTACK",
    "DEFEND",
    "EXPAND",
    "ECONOMY",
    "RESEARCH",
    "TRADE",
    "DIPLOMACY",
    "BUILD",
    "RECRUIT",
]

# Savaş gerektiren eylemler
WAR_REQUIRED_ACTIONS = {"ATTACK"}

# Diplomatik duruma göre kısıtlamalar burada değil,
# action_validator'da uygulanır.


class GameStateBuilder:
    """
    Verilen AI için fog of war uygulanmış game state üretir.
    AI yalnızca kendi bildiği bilgileri görür.
    """

    # Görüş menzili (tile sayısı olarak)
    VISION_RANGE = 4

    def build(
        self,
        turn: int,
        perspective_agent: "Country",
        all_countries: list["Country"],
        game_map: "GameMap",
        diplomacy: "DiplomacySystem",
        max_turns: int = 200,
    ) -> dict:
        """
        Belirli bir AI'ın perspektifinden game state dict'i oluştur.
        """
        r = perspective_agent.resources
        agent_id = perspective_agent.agent_id

        # Görünür tile'ları hesapla
        visible_tiles = self._get_visible_tiles(agent_id, game_map)

        # Kendi harita bilgisi
        nearby_resources = game_map.get_nearby_resources(agent_id)

        # Diğer oyuncular (fog of war ile)
        other_players = []
        for country in all_countries:
            if country.agent_id == agent_id:
                continue
            if country.status.value == "eliminated":
                continue
            known_army = self._get_known_army(
                agent_id, country, game_map, visible_tiles
            )
            rel = diplomacy.get_relation(agent_id, country.agent_id)
            other_players.append({
                "id": country.agent_id,
                "known_army": known_army,
                "known_territory": country.resources.territory,
                "relation_score": round(rel.score, 1),
                "relation_status": rel.status.value,
            })

        # Mevcut eylemler (bu turn için geçerli olanlar)
        available = self._get_available_actions(
            perspective_agent, all_countries, diplomacy
        )

        # Diplomatik ilişkiler özeti
        diplomacy_summary = diplomacy.get_all_relations_dict()

        # Aktif paktlar ve bekleyen teklifler
        active_contracts = [
            {
                "id": c.contract_id,
                "type": c.contract_type.value,
                "with": c.target if c.initiator == agent_id else c.initiator,
                "turns_remaining": c.turns_remaining,
            }
            for c in diplomacy.contracts.get_active_contracts_for(agent_id)
        ]
        pending_proposals = [
            {
                "id": c.contract_id,
                "type": c.contract_type.value,
                "from": c.initiator,
                "duration": c.duration_turns,
            }
            for c in diplomacy.contracts.get_pending_proposals_for(agent_id)
        ]

        state = {
            "turn": turn,
            "max_turns": max_turns,
            "turns_remaining": max_turns - turn,
            "player": {
                "id": agent_id,
                "name": perspective_agent.name,
                **r.to_dict(),
                "score": round(perspective_agent.calculate_score(), 1),
            },
            "map": {
                "known_territory_count": r.territory,
                "nearby_resources": nearby_resources,
                "can_expand": len(game_map.get_adjacent_unowned(agent_id)) > 0,
            },
            "other_players": other_players,
            "diplomacy": diplomacy_summary,
            "active_contracts": active_contracts,
            "pending_proposals": pending_proposals,
            "diplomatic_inbox": perspective_agent.diplomatic_inbox[-6:],
            "available_actions": available,
            "action_notes": {
                "ATTACK": "Target an enemy. Costs army, may gain territory.",
                "DEFEND": "Fortify borders. Low cost, defensive bonus.",
                "EXPAND": "Claim neutral territory. Costs gold.",
                "ECONOMY": "Boost economy. Costs gold, gains food, wood and pop.",
                "RESEARCH": "Advance technology. High gold cost, long-term benefits.",
                "TRADE": "Propose trade with a player. Both gain gold and influence.",
                "DIPLOMACY": "Change diplomatic relations. Specify sub_action (PEACE/TRADE/ALLIANCE/WAR), target and optional diplomatic_message.",
                "BUILD": "Construct infrastructure. Specify sub_action (FARM/LUMBER_MILL/MINE/FORT/ROAD/CITY). Costs gold, wood, stone, iron.",
                "RECRUIT": "Train armed soldiers. Costs gold and iron.",
            }
        }
        return state

    def _get_visible_tiles(self, agent_id: str, game_map: "GameMap") -> set[tuple[int, int]]:
        """Agent'ın görebildiği tüm tile koordinatları."""
        owned = game_map.get_tiles_owned_by(agent_id)
        visible = set()
        for tile in owned:
            for dx in range(-self.VISION_RANGE, self.VISION_RANGE + 1):
                for dy in range(-self.VISION_RANGE, self.VISION_RANGE + 1):
                    nx, ny = tile.x + dx, tile.y + dy
                    if 0 <= nx < game_map.WIDTH and 0 <= ny < game_map.HEIGHT:
                        visible.add((nx, ny))
        return visible

    def _get_known_army(
        self,
        observer_id: str,
        target: "Country",
        game_map: "GameMap",
        visible_tiles: set[tuple[int, int]],
    ) -> int:
        """
        Fog of war: gözlemci sadece görüş alanındaki orduları bilir.
        Tam ordu sayısı yerine yaklaşık değer döndür.
        """
        target_tiles = game_map.get_tiles_owned_by(target.agent_id)
        visible_target_tiles = [
            t for t in target_tiles if (t.x, t.y) in visible_tiles
        ]
        if not visible_target_tiles:
            return 0  # Hiç görmüyor

        # Görülen alan oranına göre ordu tahmini
        visibility_ratio = len(visible_target_tiles) / max(1, len(target_tiles))
        known = int(target.resources.army * visibility_ratio)
        return known

    def _get_available_actions(
        self,
        country: "Country",
        all_countries: list["Country"],
        diplomacy: "DiplomacySystem",
    ) -> list[str]:
        """Bu turn için geçerli eylemleri döndür."""
        available = []
        r = country.resources

        # Temel eylemler
        available.append("DEFEND")
        available.append("ECONOMY")
        available.append("BUILD")
        available.append("EXPAND")

        if r.gold >= 40 and r.iron >= 20:
            available.append("RECRUIT")

        # Araştırma (teknoloji max değilse)
        if r.technology < r.MAX_TECHNOLOGY:
            available.append("RESEARCH")

        # Saldırı & Diplomasi (aktif düşman varsa)
        enemies = [
            c for c in all_countries
            if c.agent_id != country.agent_id
            and c.is_active()
        ]
        if enemies:
            available.append("ATTACK")
            available.append("TRADE")
            available.append("DIPLOMACY")

        return available

    def build_hash(self, state: dict) -> str:
        """Game state'in deterministik hash'ini üret (decision log için)."""
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()[:12]


class WinConditionChecker:
    """Oyun bitiş koşullarını kontrol eder."""

    def check(
        self,
        countries: list["Country"],
        turn: int,
        max_turns: int,
    ) -> Optional[tuple[str, str]]:
        """
        (winner_id, reason) tuple döndür, oyun bitmemişse None.
        """
        active = [c for c in countries if c.is_active()]

        # Eliminasyon: sadece 1 aktif kaldı
        if len(active) == 1:
            return (active[0].agent_id, "elimination")

        # Herkes elendi
        if len(active) == 0:
            return ("draw", "all_eliminated")

        # Maksimum tur doldu → skor ile belirle
        if turn >= max_turns:
            ranked = sorted(active, key=lambda c: c.calculate_score(), reverse=True)
            if len(ranked) >= 2 and ranked[0].calculate_score() == ranked[1].calculate_score():
                return ("draw", "score_tie")
            return (ranked[0].agent_id, "score_victory")

        return None

    def update_territory_counts(
        self, countries: list["Country"], game_map: "GameMap"
    ) -> None:
        """Haritadan toprak sayılarını güncelle ve eleminasyon kontrol et."""
        for country in countries:
            if not country.is_active():
                continue
            count = game_map.get_territory_count(country.agent_id)
            country.resources.territory = count

            # Eleminasyon kontrolü
            if country.resources.is_eliminated():
                country.eliminate()
