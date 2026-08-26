"""
contracts.py — Resmi Sözleşmeler (Contracts), Paktlar ve İhanet Takip Sistemi
AI modellerinin birbirleriyle bağlayıcı diplomatik paktlar yapmasını ve ihanetlerin ölçülmesini sağlar.
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any
import uuid


class ContractType(Enum):
    NON_AGGRESSION = "non_aggression"  # Saldırmazlık Paktı
    TRADE_DEAL = "trade_deal"          # Karşılıklı düzenli kaynak transferi
    DEFENSIVE_PACT = "defensive_pact"  # Ortak savunma paktı


class ContractStatus(Enum):
    PROPOSED = "proposed"              # Teklif edildi
    ACTIVE = "active"                  # Yürürlükte
    FULFILLED = "fulfilled"            # Başarıyla tamamlandı
    VIOLATED = "violated"              # Biri anlaşmayı bozdu (İHANET)
    REJECTED = "rejected"              # Reddedildi


@dataclass
class Contract:
    contract_id: str
    contract_type: ContractType
    initiator: str
    target: str
    duration_turns: int
    start_turn: int
    turns_remaining: int
    status: ContractStatus = ContractStatus.PROPOSED
    terms: dict[str, Any] = field(default_factory=dict)
    violated_by: Optional[str] = None
    violation_turn: Optional[int] = None

    def is_active(self) -> bool:
        return self.status == ContractStatus.ACTIVE

    def tick(self, current_turn: int) -> Optional[str]:
        """Her tur pakt süresini 1 azaltır."""
        if self.status != ContractStatus.ACTIVE:
            return None
        self.turns_remaining -= 1
        if self.turns_remaining <= 0:
            self.status = ContractStatus.FULFILLED
            return f"📜 Contract #{self.contract_id} ({self.contract_type.value}) between {self.initiator} and {self.target} FULFILLED successfully!"
        return None

    def violate(self, violator_id: str, turn: int) -> str:
        """Paktın süresi dolmadan bozulması (İHANET)."""
        self.status = ContractStatus.VIOLATED
        self.violated_by = violator_id
        self.violation_turn = turn
        return f"🚨 [BETRAYAL] {violator_id} VIOLATED contract #{self.contract_id} ({self.contract_type.value}) on turn {turn}!"


class ContractManager:
    """Tüm aktif, bekleyen ve geçmiş sözleşmeleri yönetir."""

    def __init__(self):
        self.contracts: dict[str, Contract] = {}
        self.total_contracts_signed: int = 0
        self.total_contracts_fulfilled: int = 0
        self.total_betrayals: int = 0

    def propose_contract(
        self,
        initiator: str,
        target: str,
        contract_type: ContractType,
        duration: int,
        turn: int,
        terms: Optional[dict] = None,
    ) -> Contract:
        cid = f"C{len(self.contracts) + 1:03d}"
        contract = Contract(
            contract_id=cid,
            contract_type=contract_type,
            initiator=initiator,
            target=target,
            duration_turns=duration,
            start_turn=turn,
            turns_remaining=duration,
            status=ContractStatus.PROPOSED,
            terms=terms or {},
        )
        self.contracts[cid] = contract
        return contract

    def accept_contract(self, contract_id: str, turn: int) -> Optional[Contract]:
        c = self.contracts.get(contract_id)
        if c and c.status == ContractStatus.PROPOSED:
            c.status = ContractStatus.ACTIVE
            c.start_turn = turn
            c.turns_remaining = c.duration_turns
            self.total_contracts_signed += 1
            return c
        return None

    def reject_contract(self, contract_id: str) -> Optional[Contract]:
        c = self.contracts.get(contract_id)
        if c and c.status == ContractStatus.PROPOSED:
            c.status = ContractStatus.REJECTED
            return c
        return None

    def get_active_contracts_for(self, agent_id: str) -> list[Contract]:
        return [
            c for c in self.contracts.values()
            if c.is_active() and (c.initiator == agent_id or c.target == agent_id)
        ]

    def get_pending_proposals_for(self, agent_id: str) -> list[Contract]:
        return [
            c for c in self.contracts.values()
            if c.status == ContractStatus.PROPOSED and c.target == agent_id
        ]

    def has_non_aggression_pact(self, agent_a: str, agent_b: str) -> Optional[Contract]:
        for c in self.contracts.values():
            if c.is_active() and c.contract_type == ContractType.NON_AGGRESSION:
                if (c.initiator == agent_a and c.target == agent_b) or (c.initiator == agent_b and c.target == agent_a):
                    return c
        return None

    def check_and_apply_violation(self, attacker_id: str, defender_id: str, turn: int) -> Optional[str]:
        """Saldırı durumunda aktif pakt varsa ihlal et ve ihanet mesajı döndür."""
        pact = self.has_non_aggression_pact(attacker_id, defender_id)
        if pact:
            self.total_betrayals += 1
            msg = pact.violate(attacker_id, turn)
            return msg
        return None

    def tick_all(self, current_turn: int) -> list[str]:
        events = []
        for c in self.contracts.values():
            if c.is_active():
                msg = c.tick(current_turn)
                if msg:
                    self.total_contracts_fulfilled += 1
                    events.append(msg)
        return events
