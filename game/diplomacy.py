"""
diplomacy.py — Diplomatik ilişkiler, Resmi Paktlar (Contracts) ve İhanet Sistemi
WAR, PEACE, TRADE, ALLIANCE + NON_AGGRESSION_PACT, TRADE_DEAL
İlişki skoru: -100 (Hostile) → 0 (Neutral) → +100 (Friendly)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

from game.contracts import ContractManager, ContractType, ContractStatus, Contract

if TYPE_CHECKING:
    from game.country import Country


class DiplomaticStatus(Enum):
    WAR = "war"
    NEUTRAL = "neutral"
    TRADE = "trade"
    ALLIANCE = "alliance"
    PEACE = "peace"


@dataclass
class DiplomaticRelation:
    agent_a: str
    agent_b: str
    score: float = 0.0                     # -100..+100
    status: DiplomaticStatus = DiplomaticStatus.NEUTRAL
    turns_in_status: int = 0               # Bu statüde kaç turdur

    ALLIANCE_MIN_TURNS = 3
    PEACE_MIN_TURNS = 2

    def is_at_war(self) -> bool:
        return self.status == DiplomaticStatus.WAR

    def is_allied(self) -> bool:
        return self.status == DiplomaticStatus.ALLIANCE

    def can_break_alliance(self) -> bool:
        return self.turns_in_status >= self.ALLIANCE_MIN_TURNS

    def tick(self) -> None:
        self.turns_in_status += 1
        if self.status == DiplomaticStatus.WAR:
            self.score = max(-100, self.score - 5)
        elif self.status in (DiplomaticStatus.PEACE, DiplomaticStatus.ALLIANCE):
            self.score = min(100, self.score + 2)
        elif self.status == DiplomaticStatus.TRADE:
            self.score = min(100, self.score + 3)


class DiplomacySystem:
    """
    Tüm ülkeler arası diplomatik ilişkileri ve resmi paktları yönetir.
    """

    def __init__(self, agent_ids: list[str]):
        self.relations: dict[frozenset, DiplomaticRelation] = {}
        self.contracts = ContractManager()
        for i, a in enumerate(agent_ids):
            for b in agent_ids[i+1:]:
                key = frozenset({a, b})
                self.relations[key] = DiplomaticRelation(a, b)

    def _key(self, a: str, b: str) -> frozenset:
        return frozenset({a, b})

    def get_relation(self, a: str, b: str) -> DiplomaticRelation:
        return self.relations[self._key(a, b)]

    def get_score(self, a: str, b: str) -> float:
        return self.get_relation(a, b).score

    def is_at_war(self, a: str, b: str) -> bool:
        return self.get_relation(a, b).is_at_war()

    def is_allied(self, a: str, b: str) -> bool:
        return self.get_relation(a, b).is_allied()

    def tick_all(self, current_turn: int = 1) -> list[str]:
        for rel in self.relations.values():
            rel.tick()
        return self.contracts.tick_all(current_turn)

    # ── Eylem uygulayıcıları ────────────────────────────────────────

    def apply_declare_war(
        self, initiator: "Country", target: "Country", turn: int = 1
    ) -> str:
        rel = self.get_relation(initiator.agent_id, target.agent_id)

        if rel.status == DiplomaticStatus.WAR:
            return f"Already at war with {target.agent_id}."

        # Aktif sözleşme ihlali kontrolü (İHANET)
        violation_msg = self.contracts.check_and_apply_violation(initiator.agent_id, target.agent_id, turn)
        is_betrayal = rel.is_allied() or (violation_msg is not None)

        rel.status = DiplomaticStatus.WAR
        rel.turns_in_status = 0
        rel.score -= 50 if is_betrayal else 20

        if is_betrayal:
            initiator.total_betrayals += 1
            if violation_msg:
                return violation_msg
            return (f"🚨 [BETRAYAL] {initiator.agent_id} BETRAYED alliance and declared WAR on {target.agent_id}!")
        return f"{initiator.agent_id} declared WAR on {target.agent_id}."

    def apply_peace(
        self, initiator: "Country", target: "Country"
    ) -> str:
        rel = self.get_relation(initiator.agent_id, target.agent_id)
        if rel.status == DiplomaticStatus.PEACE:
            return f"Already at peace with {target.agent_id}."
        if rel.status != DiplomaticStatus.WAR:
            return f"Cannot propose peace: not at war with {target.agent_id}."

        rel.status = DiplomaticStatus.PEACE
        rel.turns_in_status = 0
        rel.score += 15
        return f"{initiator.agent_id} made PEACE with {target.agent_id}."

    def apply_trade(
        self, initiator: "Country", target: "Country"
    ) -> str:
        rel = self.get_relation(initiator.agent_id, target.agent_id)
        if rel.is_at_war():
            return f"Cannot trade: at war with {target.agent_id}."
        if rel.status == DiplomaticStatus.TRADE:
            return f"Already trading with {target.agent_id}."

        rel.status = DiplomaticStatus.TRADE
        rel.turns_in_status = 0
        rel.score += 10

        trade_gold = 50.0
        initiator.resources.gold += trade_gold
        target.resources.gold += trade_gold
        initiator.resources.influence += 5.0
        target.resources.influence += 5.0
        initiator.total_trades += 1

        return (f"{initiator.agent_id} established TRADE with {target.agent_id}. "
                f"Both gain {trade_gold:.0f} gold & +5 influence.")

    def apply_alliance(
        self, initiator: "Country", target: "Country"
    ) -> str:
        rel = self.get_relation(initiator.agent_id, target.agent_id)
        if rel.is_at_war():
            return f"Cannot ally: at war with {target.agent_id}."
        if rel.is_allied():
            return f"Already allied with {target.agent_id}."
        if initiator.resources.influence < 20.0:
            return f"Alliance failed: Need 20 Influence (have {initiator.resources.influence:.0f})."
        if rel.score < 20:
            return (f"Alliance rejected by {target.agent_id}: relation score {rel.score:.0f} too low (need 20+).")

        initiator.resources.influence -= 20.0
        rel.status = DiplomaticStatus.ALLIANCE
        rel.turns_in_status = 0
        rel.score += 20
        initiator.total_alliances += 1

        # Otomatik saldırmazlık sözleşmesi oluştur
        self.contracts.propose_contract(
            initiator=initiator.agent_id,
            target=target.agent_id,
            contract_type=ContractType.NON_AGGRESSION,
            duration=10,
            turn=1,
        )
        self.contracts.accept_contract(f"C{len(self.contracts.contracts):03d}", turn=1)

        return f"{initiator.agent_id} formed ALLIANCE with {target.agent_id} (Signed 10-turn Non-Aggression Pact)."

    def apply_diplomacy_action(
        self, initiator: "Country", target: "Country", sub_action: str, turn: int = 1
    ) -> str:
        """Genel DIPLOMACY dispatcher."""
        sa = sub_action.upper()
        if sa == "PEACE":
            return self.apply_peace(initiator, target)
        elif sa == "TRADE":
            return self.apply_trade(initiator, target)
        elif sa == "ALLIANCE":
            return self.apply_alliance(initiator, target)
        elif sa == "WAR":
            return self.apply_declare_war(initiator, target, turn)
        else:
            return f"Unknown diplomacy sub-action: {sub_action}"

    def get_all_relations_dict(self) -> list[dict]:
        result = []
        for rel in self.relations.values():
            result.append({
                "between": [rel.agent_a, rel.agent_b],
                "score": round(rel.score, 1),
                "status": rel.status.value,
            })
        return result
