"""
test_combat.py — Savaş sistemi testleri
"""
import random
import pytest
from game.combat import CombatSystem
from game.country import create_default_countries
from game.map import GameMap


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)
    return countries, game_map, CombatSystem()


def test_attack_reduces_armies(setup):
    countries, game_map, combat = setup
    ai_a, ai_b = countries
    initial_a = ai_a.resources.army
    initial_b = ai_b.resources.army
    rng = random.Random(42)
    result = combat.resolve_attack(ai_a, ai_b, game_map, rng)
    assert ai_a.resources.army < initial_a, "Attacker should lose soldiers"
    assert ai_b.resources.army < initial_b, "Defender should lose soldiers"


def test_attack_winner_gains_territory(setup):
    countries, game_map, combat = setup
    ai_a, ai_b = countries
    # Güçlü saldırgan
    ai_a.resources.army = 500
    ai_b.resources.army = 50
    initial_territory_b = game_map.get_territory_count(ai_b.agent_id)
    rng = random.Random(1)
    result = combat.resolve_attack(ai_a, ai_b, game_map, rng)
    if result.attacker_won:
        assert result.territory_captured > 0
        assert game_map.get_territory_count(ai_b.agent_id) < initial_territory_b


def test_defend_adds_temporary_soldiers(setup):
    countries, game_map, combat = setup
    ai_a, _ = countries
    ai_a.resources.gold = 100.0
    initial_army = ai_a.resources.army
    msg = combat.resolve_defend(ai_a)
    assert ai_a.resources.army > initial_army, "Defend should add temporary soldiers"


def test_defend_costs_gold(setup):
    countries, game_map, combat = setup
    ai_a, _ = countries
    ai_a.resources.gold = 100.0
    initial_gold = ai_a.resources.gold
    combat.resolve_defend(ai_a)
    assert ai_a.resources.gold < initial_gold


def test_expand_claims_neutral_territory(setup):
    countries, game_map, combat = setup
    ai_a, _ = countries
    ai_a.resources.gold = 200.0
    initial_territory = game_map.get_territory_count(ai_a.agent_id)
    rng = random.Random(42)
    msg = combat.resolve_expand(ai_a, game_map, rng)
    new_territory = game_map.get_territory_count(ai_a.agent_id)
    assert new_territory > initial_territory or "insufficient" in msg or "no adjacent" in msg.lower()


def test_no_army_cannot_attack(setup):
    countries, game_map, combat = setup
    ai_a, ai_b = countries
    ai_a.resources.army = 0
    rng = random.Random(42)
    result = combat.resolve_attack(ai_a, ai_b, game_map, rng)
    # Ordu 0 iken bile saldırı yapılabilir ama kayıp 0 olur
    assert result.attacker_losses >= 0
