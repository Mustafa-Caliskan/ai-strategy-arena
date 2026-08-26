"""
test_benchmark.py — Elo ve Benchmark Runner Testleri
"""
import pytest
from benchmark.elo_system import EloSystem
from benchmark.benchmark_runner import BenchmarkRunner
from ai.baseline_agents import GreedyProvider, DefensiveProvider, RandomProvider


def test_elo_system_updates_ratings_properly():
    elo = EloSystem(k_factor=32.0, initial_elo=1200.0)
    
    # A beats B
    new_a, new_b = elo.record_match(
        agent_a="Agent_A", agent_b="Agent_B", winner="Agent_A", turns_played=10
    )
    assert new_a > 1200.0
    assert new_b < 1200.0
    assert round(new_a + new_b, 1) == 2400.0  # Zero-sum rating exchange
    
    # Leaderboard sıralaması
    board = elo.get_leaderboard()
    assert board[0].agent_id == "Agent_A"
    assert board[1].agent_id == "Agent_B"


def test_benchmark_runner_executes_mini_tournament():
    runner = BenchmarkRunner(max_turns=10, base_seed=42)
    
    factories = {
        "Greedy": lambda aid, s: GreedyProvider(aid, seed=s),
        "Defensive": lambda aid, s: DefensiveProvider(aid, seed=s),
        "Random": lambda aid, s: RandomProvider(aid, seed=s),
    }
    
    report = runner.run_tournament(factories, rounds_per_pair=1)
    
    # 3 bot -> 3 çift x 1 round = 3 maç
    assert report.total_matches == 3
    assert len(report.matches) == 3
    
    leaderboard = runner.elo_system.get_leaderboard()
    assert len(leaderboard) == 3
    
    md = report.summary_markdown()
    assert "Benchmark Ligi Raporu" in md
    assert "Greedy" in md
