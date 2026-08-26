"""
benchmark_runner.py — Deterministik Turnuva ve Karşılaştırma Motoru
Tüm baseline botları ve LLM modellerini eşleştirip Elo puanlarını hesaplar.
"""
from __future__ import annotations
import itertools
import logging
from typing import Callable, Any
from dataclasses import dataclass, field

from game.country import Country, create_default_countries
from game.map import GameMap
from simulation.turn_manager import TurnManager
from benchmark.elo_system import EloSystem, AgentStats
from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    match_id: int
    seed: int
    agent_a: str
    agent_b: str
    winner: str | None
    win_reason: str
    turns_played: int
    final_score_a: float
    final_score_b: float


@dataclass
class TournamentReport:
    total_matches: int
    matches: list[MatchResult] = field(default_factory=list)
    elo_system: EloSystem = field(default_factory=EloSystem)

    def summary_markdown(self) -> str:
        md = []
        md.append("# 🏆 AI Strategy Arena — Benchmark Ligi Raporu\n")
        md.append(f"**Toplam Oynanan Maç:** {self.total_matches}\n")
        md.append("## 📊 Elo Sıralaması (Leaderboard)\n")
        md.append("| Sıra | Ajan / Model | Elo Puanı | G / M / B | Kazanma % | Ort. Skor | İhanet Sayısı |")
        md.append("|---|---|---|---|---|---|---|")
        for rank, a in enumerate(self.elo_system.get_leaderboard(), 1):
            gmb = f"{a.wins} / {a.losses} / {a.draws}"
            md.append(f"| {rank} | **{a.agent_id}** | `{a.elo:.1f}` | {gmb} | %{a.win_rate:.1f} | {a.avg_score:.1f} | {a.total_betrayals} |")
        return "\n".join(md)


class BenchmarkRunner:
    """
    Belirtilen botlar arasında lig maçları düzenleyen ve Elo sıralaması çıkaran motor.
    """

    def __init__(self, max_turns: int = 100, base_seed: int = 1000):
        self.max_turns = max_turns
        self.base_seed = base_seed
        self.elo_system = EloSystem()

    def run_tournament(
        self,
        provider_factories: dict[str, Callable[[str, int], AIProvider]],
        rounds_per_pair: int = 2,
    ) -> TournamentReport:
        """
        Tüm ajan kombinasyonlarını çiftler halinde (round-robin) yarıştırır.
        """
        agent_names = list(provider_factories.keys())
        pairs = list(itertools.combinations(agent_names, 2))
        report = TournamentReport(total_matches=len(pairs) * rounds_per_pair, elo_system=self.elo_system)

        match_id = 0
        for name_a, name_b in pairs:
            for r in range(rounds_per_pair):
                match_id += 1
                seed = self.base_seed + match_id
                res = self._run_single_match(
                    match_id=match_id,
                    seed=seed,
                    name_a=name_a,
                    factory_a=provider_factories[name_a],
                    name_b=name_b,
                    factory_b=provider_factories[name_b],
                )
                report.matches.append(res)

        return report

    def _run_single_match(
        self,
        match_id: int,
        seed: int,
        name_a: str,
        factory_a: Callable[[str, int], AIProvider],
        name_b: str,
        factory_b: Callable[[str, int], AIProvider],
    ) -> MatchResult:
        game_map = GameMap(seed=seed)
        countries = [
            Country(agent_id=name_a, name=f"Empire {name_a}", color=(220, 50, 50), capital_x=2, capital_y=10),
            Country(agent_id=name_b, name=f"Empire {name_b}", color=(50, 100, 220), capital_x=17, capital_y=10),
        ]
        for c in countries:
            c.resources.territory = game_map.get_territory_count(c.agent_id)

        providers = {
            name_a: factory_a(name_a, seed),
            name_b: factory_b(name_b, seed + 1),
        }

        manager = TurnManager(
            countries=countries,
            providers=providers,
            game_map=game_map,
            max_turns=self.max_turns,
            seed=seed,
        )

        winner, reason = manager.run_game_sync()
        country_a = next(c for c in countries if c.agent_id == name_a)
        country_b = next(c for c in countries if c.agent_id == name_b)

        score_a = country_a.calculate_score()
        score_b = country_b.calculate_score()

        # Elo puanlarını güncelle
        self.elo_system.record_match(
            agent_a=name_a,
            agent_b=name_b,
            winner=winner,
            score_a=score_a,
            score_b=score_b,
            turns_played=manager.current_turn,
            betrayals_a=country_a.total_betrayals,
            betrayals_b=country_b.total_betrayals,
        )

        return MatchResult(
            match_id=match_id,
            seed=seed,
            agent_a=name_a,
            agent_b=name_b,
            winner=winner,
            win_reason=reason,
            turns_played=manager.current_turn,
            final_score_a=score_a,
            final_score_b=score_b,
        )
