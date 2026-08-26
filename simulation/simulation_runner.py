"""
simulation_runner.py — Headless batch simülasyon çalıştırıcı
python main.py --batch 100 ile çağrılır.
"""
from __future__ import annotations
import asyncio
import logging
import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.country import create_default_countries
from game.map import GameMap
from simulation.turn_manager import TurnManager

if TYPE_CHECKING:
    from ai.base_provider import AIProvider


logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    run_id: int
    seed: int
    winner: str | None
    win_reason: str
    turns_played: int
    final_scores: dict[str, float]
    action_stats: dict[str, dict[str, int]]


@dataclass
class BatchReport:
    total_runs: int
    results: list[SimulationResult] = field(default_factory=list)

    def win_rates(self) -> dict[str, float]:
        wins: dict[str, int] = {}
        draws = 0
        for r in self.results:
            if r.winner and r.winner != "draw":
                wins[r.winner] = wins.get(r.winner, 0) + 1
            else:
                draws += 1
        rates = {k: v / self.total_runs * 100 for k, v in wins.items()}
        if draws:
            rates["draw"] = draws / self.total_runs * 100
        return rates

    def avg_turns(self) -> float:
        if not self.results:
            return 0.0
        return statistics.mean(r.turns_played for r in self.results)

    def action_distribution(self) -> dict[str, dict[str, float]]:
        """Tüm simülasyonlardaki ortalama action dağılımı."""
        totals: dict[str, dict[str, int]] = {}
        counts: dict[str, int] = {}
        for r in self.results:
            for agent_id, actions in r.action_stats.items():
                if agent_id not in totals:
                    totals[agent_id] = {}
                    counts[agent_id] = 0
                counts[agent_id] += 1
                for a, n in actions.items():
                    totals[agent_id][a] = totals[agent_id].get(a, 0) + n

        dist: dict[str, dict[str, float]] = {}
        for agent_id, actions in totals.items():
            total_actions = sum(actions.values())
            dist[agent_id] = {
                a: round(n / total_actions * 100, 1)
                for a, n in actions.items()
            } if total_actions > 0 else {}
        return dist

    def print_report(self) -> None:
        print("\n" + "="*50)
        print(f"BATCH SIMULATION REPORT ({self.total_runs} runs)")
        print("="*50)
        print(f"\nWin Rates:")
        for agent, rate in self.win_rates().items():
            print(f"  {agent}: {rate:.1f}%")
        print(f"\nAverage turns per game: {self.avg_turns():.1f}")
        print(f"\nAction Distribution:")
        for agent, actions in self.action_distribution().items():
            print(f"  {agent}:")
            for action, pct in sorted(actions.items(), key=lambda x: -x[1]):
                print(f"    {action:12s}: {pct:.1f}%")
        print("="*50 + "\n")


class SimulationRunner:
    """
    Birden fazla oyunu sırayla çalıştıran batch runner.
    """

    def __init__(
        self,
        provider_factory,  # Callable[[agent_id, seed], AIProvider]
        max_turns: int = 200,
        base_seed: int = 42,
    ):
        self.provider_factory = provider_factory
        self.max_turns = max_turns
        self.base_seed = base_seed

    def run_batch(self, num_runs: int) -> BatchReport:
        report = BatchReport(total_runs=num_runs)
        for i in range(num_runs):
            seed = self.base_seed + i
            try:
                result = self._run_single(i + 1, seed)
                report.results.append(result)
                if (i + 1) % 10 == 0:
                    logger.info(f"Completed {i+1}/{num_runs} runs.")
            except Exception as e:
                logger.error(f"Run {i+1} failed: {e}")
        return report

    def _run_single(self, run_id: int, seed: int) -> SimulationResult:
        countries = create_default_countries()
        game_map = GameMap(seed=seed)
        # Başlangıç toprak sayısını ayarla
        for c in countries:
            c.resources.territory = game_map.get_territory_count(c.agent_id)

        providers = {
            c.agent_id: self.provider_factory(c.agent_id, seed)
            for c in countries
        }

        manager = TurnManager(
            countries=countries,
            providers=providers,
            game_map=game_map,
            max_turns=self.max_turns,
            seed=seed,
            log_dir="logs/decisions",
        )

        winner, reason = manager.run_game_sync()

        final_scores = {c.agent_id: c.calculate_score() for c in countries}

        return SimulationResult(
            run_id=run_id,
            seed=seed,
            winner=winner,
            win_reason=reason,
            turns_played=manager.current_turn,
            final_scores=final_scores,
            action_stats=manager.events.get_action_stats(),
        )
