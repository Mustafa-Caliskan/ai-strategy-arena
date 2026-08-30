"""
country.py — Ülke/AI agent varlığı
Her AI'ın oyun içindeki kimliği ve durumu.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from game.resources import Resources


class AgentStatus(Enum):
    ACTIVE = "active"
    ELIMINATED = "eliminated"


@dataclass
class Country:
    """Bir AI'ın oyundaki temsilcisi."""
    agent_id: str
    name: str
    color: tuple[int, int, int]          # RGB, UI için
    resources: Resources = field(default_factory=Resources)
    status: AgentStatus = AgentStatus.ACTIVE
    capital_x: int = 0
    capital_y: int = 0
    garrison_army: int = 80
    diplomatic_inbox: list[dict] = field(default_factory=list)

    # İstatistikler (replay ve analytics için)
    total_attacks: int = 0
    total_defenses: int = 0
    total_trades: int = 0
    total_alliances: int = 0
    total_betrayals: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    turns_survived: int = 0
    kills: int = 0                        # Elimine ettiği AI sayısı

    def receive_message(self, from_agent: str, message: str, turn: int) -> None:
        self.diplomatic_inbox.append({
            "from": from_agent,
            "message": message,
            "turn": turn,
        })
        self.total_messages_received += 1

    def is_active(self) -> bool:
        return self.status == AgentStatus.ACTIVE

    def eliminate(self) -> None:
        self.status = AgentStatus.ELIMINATED

    def calculate_score(self) -> float:
        """
        Score = Territory*3 + Economy + Military + Technology*10 + Diplomatic
        Kazanma koşulu için kullanılır.
        """
        r = self.resources
        territory_score = r.territory * 3.0
        economy_score = (r.gold * 0.1) + (r.food * 0.05)
        military_score = r.army * 1.5
        tech_score = r.technology * 10.0
        pop_score = r.population * 0.2
        return territory_score + economy_score + military_score + tech_score + pop_score

    def to_public_dict(self, known_army: Optional[int] = None) -> dict:
        """Fog of war ile başka AI'ın göreceği bilgiler."""
        return {
            "id": self.agent_id,
            "known_army": known_army if known_army is not None else self.resources.army,
            "known_territory": self.resources.territory,
            "status": self.status.value,
        }

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "resources": self.resources.to_dict(),
            "score": round(self.calculate_score(), 1),
            "capital": {"x": self.capital_x, "y": self.capital_y},
            "stats": {
                "attacks": self.total_attacks,
                "defenses": self.total_defenses,
                "trades": self.total_trades,
                "alliances": self.total_alliances,
                "turns_survived": self.turns_survived,
            }
        }


def create_default_countries() -> list[Country]:
    """
    İlk MVP için iki eşit başlangıç ülkesi oluştur.
    Her iki AI da tamamen aynı kaynaklarla başlar.
    """
    default_resources_a = Resources(
        gold=500.0,
        food=400.0,
        population=150,
        army=80,
        territory=0,          # harita taramasıyla güncellenir
        technology=1,
    )
    default_resources_b = Resources(
        gold=500.0,
        food=400.0,
        population=150,
        army=80,
        territory=0,
        technology=1,
    )

    ai_a = Country(
        agent_id="AI_A",
        name="OpenAI (GPT-4o)",
        color=(220, 50, 50),     # Kırmızı
        resources=default_resources_a,
        capital_x=2,
        capital_y=10,
    )
    ai_b = Country(
        agent_id="AI_B",
        name="DeepSeek",
        color=(50, 100, 220),    # Mavi
        resources=default_resources_b,
        capital_x=17,
        capital_y=10,
    )
    bandits = Country(
        agent_id="BANDITS",
        name="Kara Sancaklılar",
        color=(30, 30, 35),      # Siyah / Kara Sancak
        resources=Resources(gold=300.0, food=300.0, population=100, army=100, territory=0, technology=1),
        capital_x=10,
        capital_y=2,
    )
    return [ai_a, ai_b, bandits]
