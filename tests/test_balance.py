"""
test_balance.py — Anti-Dominant Strategy & AI Diversity Testleri
Spec Bölüm 33 ve 34'ün implementasyonu.

Test 1: Sürekli ATTACK oynayan AI ne olur?
Test 2: Sürekli ECONOMY oynayan AI ne olur?
Test 3: Sürekli DEFEND oynayan AI ne olur?
Test 4: Sürekli ALLIANCE/DIPLOMACY oynayan AI ne olur?
Test 5: AI Diversity - farklı seed'lerde action dağılımı
"""
import asyncio
import json
import pytest
from ai.random_provider import RandomProvider
from game.country import create_default_countries
from game.map import GameMap
from simulation.turn_manager import TurnManager


TURNS = 80   # Yeterince uzun oyun


def make_fixed_provider(agent_id: str, fixed_action: str, seed: int = 0):
    """Her zaman aynı eylemi seçen sabit AI."""
    from ai.base_provider import AIProvider
    import json as _json

    class FixedProvider(AIProvider):
        def __init__(self):
            super().__init__(agent_id, f"fixed-{fixed_action}", 0.0)
            self._action = fixed_action

        async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
            self._call_count += 1
            # DIPLOMACY için geçerli hedef bul
            try:
                import re, json as j
                m = re.search(r'\{.*\}', user_prompt, re.DOTALL)
                if m:
                    state = j.loads(m.group())
                    others = state.get("other_players", [])
                    target = others[0]["id"] if others else None
                else:
                    target = None
            except Exception:
                target = None

            resp = {
                "action": self._action,
                "target": target,
                "sub_action": "PEACE" if self._action == "DIPLOMACY" else None,
                "reason": f"Always {self._action} strategy",
            }
            return _json.dumps(resp)

    return FixedProvider()


def run_single_game(provider_a, provider_b, seed: int = 42) -> dict:
    """Tek bir oyun çalıştır, sonuçları döndür."""
    countries = create_default_countries()
    game_map = GameMap(seed=seed)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)

    manager = TurnManager(
        countries=countries,
        providers={"AI_A": provider_a, "AI_B": provider_b},
        game_map=game_map,
        max_turns=TURNS,
        seed=seed,
        log_dir="logs/balance_tests",
    )
    winner, reason = manager.run_game_sync()
    return {
        "winner": winner,
        "reason": reason,
        "turns": manager.current_turn,
        "scores": {c.agent_id: round(c.calculate_score(), 1) for c in countries},
        "action_stats": manager.events.get_action_stats(),
        "territory": {c.agent_id: c.resources.territory for c in countries},
        "army": {c.agent_id: c.resources.army for c in countries},
    }


# ──────────────────────────────────────────────────────────────────
# TEST 1: Sürekli ATTACK
# ──────────────────────────────────────────────────────────────────

def test_always_attack_vs_balanced():
    """
    Sürekli ATTACK oynayan AI, dengeli (random) AI'ya karşı
    mutlaka kazanmamalı — saldırının bir dezavantajı olmalı.
    """
    results = []
    for seed in range(5):
        attacker  = make_fixed_provider("AI_A", "ATTACK", seed)
        balanced  = RandomProvider("AI_B", seed=seed)
        r = run_single_game(attacker, balanced, seed=seed)
        results.append(r)

    attacker_wins = sum(1 for r in results if r["winner"] == "AI_A")
    print(f"\n[ATTACK Test] AI_A(always ATTACK) wins: {attacker_wins}/5")
    for i, r in enumerate(results):
        print(f"  Seed {i}: winner={r['winner']} turns={r['turns']} "
              f"scores={r['scores']} army={r['army']}")

    # Sürekli ATTACK %100 kazanmamalı
    assert attacker_wins < 5, \
        "DOMINANT STRATEGY DETECTED: Always ATTACK wins every game!"


# ──────────────────────────────────────────────────────────────────
# TEST 2: Sürekli ECONOMY
# ──────────────────────────────────────────────────────────────────

def test_always_economy_vs_balanced():
    """
    Sürekli ECONOMY oynayan AI, dengeli AI'ya karşı
    mutlaka kazanmamalı.
    """
    results = []
    for seed in range(5):
        economist = make_fixed_provider("AI_A", "ECONOMY", seed)
        balanced  = RandomProvider("AI_B", seed=seed)
        r = run_single_game(economist, balanced, seed=seed)
        results.append(r)

    economist_wins = sum(1 for r in results if r["winner"] == "AI_A")
    print(f"\n[ECONOMY Test] AI_A(always ECONOMY) wins: {economist_wins}/5")
    for i, r in enumerate(results):
        print(f"  Seed {i}: winner={r['winner']} turns={r['turns']} "
              f"scores={r['scores']}")

    assert economist_wins < 5, \
        "DOMINANT STRATEGY DETECTED: Always ECONOMY wins every game!"


# ──────────────────────────────────────────────────────────────────
# TEST 3: Sürekli DEFEND
# ──────────────────────────────────────────────────────────────────

def test_always_defend_loses_territory():
    """
    Sürekli DEFEND oynayan AI toprak kazanamaz.
    Rakip EXPAND yaparken toprak farkı açılmalı.
    """
    results = []
    for seed in range(5):
        defender  = make_fixed_provider("AI_A", "DEFEND", seed)
        expander  = make_fixed_provider("AI_B", "EXPAND", seed)
        r = run_single_game(defender, expander, seed=seed)
        results.append(r)

    # Savunmacının toprağı genelde genişleyici'den az olmalı
    defender_more_territory = sum(
        1 for r in results
        if r["territory"]["AI_A"] > r["territory"]["AI_B"]
    )
    print(f"\n[DEFEND Test] Defender has more territory: {defender_more_territory}/5")
    for i, r in enumerate(results):
        print(f"  Seed {i}: territory A={r['territory']['AI_A']} "
              f"B={r['territory']['AI_B']} winner={r['winner']}")

    assert defender_more_territory < 4, \
        "BALANCE ISSUE: Always DEFEND outperforms EXPAND in territory!"


# ──────────────────────────────────────────────────────────────────
# TEST 4: Sürekli DIPLOMACY
# ──────────────────────────────────────────────────────────────────

def test_always_diplomacy_vs_attacker():
    """
    Sürekli DIPLOMACY/PEACE oynayan AI, saldırgan AI'ya karşı
    tek başına hayatta kalamamalı.
    """
    results = []
    for seed in range(5):
        diplomat  = make_fixed_provider("AI_A", "DIPLOMACY", seed)
        attacker  = make_fixed_provider("AI_B", "ATTACK", seed)
        r = run_single_game(diplomat, attacker, seed=seed)
        results.append(r)

    diplomat_wins = sum(1 for r in results if r["winner"] == "AI_A")
    print(f"\n[DIPLOMACY Test] AI_A(always DIPLOMACY) wins vs attacker: {diplomat_wins}/5")
    for i, r in enumerate(results):
        print(f"  Seed {i}: winner={r['winner']} turns={r['turns']}")

    # Sadece diplomasi oynayan saldırgan karşısında çok kazanmamalı
    assert diplomat_wins <= 3, \
        "BALANCE ISSUE: Pure diplomacy too effective against attackers!"


# ──────────────────────────────────────────────────────────────────
# TEST 5: AI Diversity
# ──────────────────────────────────────────────────────────────────

def test_random_ai_action_diversity():
    """
    Random AI 10 farklı seed'de oynandığında
    hiçbir eylem %90'dan fazla dominant olmamalı.
    """
    all_actions = {}
    for seed in range(10):
        a = RandomProvider("AI_A", seed=seed)
        b = RandomProvider("AI_B", seed=seed + 100)
        r = run_single_game(a, b, seed=seed)
        for agent, actions in r["action_stats"].items():
            if agent not in all_actions:
                all_actions[agent] = {}
            for action, count in actions.items():
                all_actions[agent][action] = all_actions[agent].get(action, 0) + count

    print("\n[DIVERSITY Test] Action distribution across 10 seeds:")
    for agent, actions in all_actions.items():
        total = sum(actions.values())
        print(f"  {agent}:")
        for action, count in sorted(actions.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            print(f"    {action:12s}: {pct:.1f}%")

        # Hiçbir eylem %75'ten fazla olmamalı
        for action, count in actions.items():
            pct = count / total * 100
            assert pct < 75, \
                f"DIVERSITY ISSUE: {agent} plays {action} {pct:.1f}% of the time!"


# ──────────────────────────────────────────────────────────────────
# TEST 6: Oyun her zaman sonuçlanıyor mu?
# ──────────────────────────────────────────────────────────────────

def test_game_always_terminates():
    """Oyun her durumda max_turns içinde bitmeli."""
    for seed in range(5):
        a = RandomProvider("AI_A", seed=seed)
        b = RandomProvider("AI_B", seed=seed + 50)
        r = run_single_game(a, b, seed=seed)
        assert r["winner"] is not None, f"Game seed {seed} has no winner!"
        assert r["turns"] <= TURNS, f"Game seed {seed} exceeded max turns!"
        print(f"  Seed {seed}: winner={r['winner']} turns={r['turns']}")
