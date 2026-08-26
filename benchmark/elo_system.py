"""
elo_system.py — Elo Derecelendirme ve Lig Sıralama Motoru
LLM modellerinin ve baseline botların stratejik güçlerini sıralamak için standart FIDE Elo sistemi.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentStats:
    agent_id: str
    elo: float = 1200.0
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_score: float = 0.0
    total_turns_survived: int = 0
    total_betrayals: int = 0

    @property
    def win_rate(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return (self.wins / self.matches_played) * 100.0

    @property
    def avg_score(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return self.total_score / self.matches_played


class EloSystem:
    """
    Tüm katılımcıların Elo puanlarını ve lig sıralamasını yönetir.
    """

    def __init__(self, k_factor: float = 32.0, initial_elo: float = 1200.0):
        self.k_factor = k_factor
        self.initial_elo = initial_elo
        self.agents: dict[str, AgentStats] = {}

    def register_agent(self, agent_id: str) -> AgentStats:
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentStats(agent_id=agent_id, elo=self.initial_elo)
        return self.agents[agent_id]

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """A ajanının B ajanına karşı beklenen kazanma olasılığı (0.0 - 1.0)."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def record_match(
        self,
        agent_a: str,
        agent_b: str,
        winner: Optional[str],
        score_a: float = 0.0,
        score_b: float = 0.0,
        turns_played: int = 1,
        betrayals_a: int = 0,
        betrayals_b: int = 0,
    ) -> tuple[float, float]:
        """
        Maç sonucunu kaydeder ve yeni Elo puanlarını döndürür: (new_elo_a, new_elo_b).
        winner == agent_a -> A kazandı
        winner == agent_b -> B kazandı
        winner is None or "draw" -> Berabere
        """
        sa = self.register_agent(agent_a)
        sb = self.register_agent(agent_b)

        exp_a = self.expected_score(sa.elo, sb.elo)
        exp_b = self.expected_score(sb.elo, sa.elo)

        if winner == agent_a:
            actual_a, actual_b = 1.0, 0.0
            sa.wins += 1
            sb.losses += 1
        elif winner == agent_b:
            actual_a, actual_b = 0.0, 1.0
            sb.wins += 1
            sa.losses += 1
        else:
            actual_a, actual_b = 0.5, 0.5
            sa.draws += 1
            sb.draws += 1

        # Elo güncelle
        sa.elo += self.k_factor * (actual_a - exp_a)
        sb.elo += self.k_factor * (actual_b - exp_b)

        # İstatistikler
        sa.matches_played += 1
        sb.matches_played += 1
        sa.total_score += score_a
        sb.total_score += score_b
        sa.total_turns_survived += turns_played
        sb.total_turns_survived += turns_played
        sa.total_betrayals += betrayals_a
        sb.total_betrayals += betrayals_b

        return sa.elo, sb.elo

    def get_leaderboard(self) -> list[AgentStats]:
        """Elo puanına göre sıralı lig tablosu."""
        return sorted(self.agents.values(), key=lambda a: a.elo, reverse=True)

    def print_leaderboard(self) -> str:
        """Konsol ve raporlar için şık ASCII lig tablosu üretir."""
        board = self.get_leaderboard()
        lines = []
        lines.append("=" * 78)
        lines.append(f"{'RANK':<5} {'AGENT ID':<20} {'ELO':<8} {'W/L/D':<12} {'WIN %':<8} {'AVG SCORE':<10} {'BETRAYALS':<10}")
        lines.append("-" * 78)
        for rank, a in enumerate(board, 1):
            wld = f"{a.wins}/{a.losses}/{a.draws}"
            lines.append(
                f"{rank:<5} {a.agent_id:<20} {a.elo:<8.1f} {wld:<12} {a.win_rate:<8.1f}% {a.avg_score:<10.1f} {a.total_betrayals:<10}"
            )
        lines.append("=" * 78)
        output = "\n".join(lines)
        return output
