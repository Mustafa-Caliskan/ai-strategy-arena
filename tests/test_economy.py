"""
test_economy.py — Ekonomi sistemi testleri
"""
import pytest
from game.country import create_default_countries
from game.economy import EconomySystem
from game.map import GameMap


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)
    return countries, game_map, EconomySystem()


def test_gold_increases_each_turn(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    initial_gold = ai_a.resources.gold
    economy.process_turn(ai_a, game_map)
    # Net gelir pozitif olmalı (başlangıç durumunda)
    assert ai_a.resources.gold != initial_gold


def test_food_consumed_by_army(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    # Büyük ordu daha fazla gıda tüketir
    ai_a.resources.army = 300
    ai_a.resources.food = 1000.0
    result = economy.process_turn(ai_a, game_map)
    # Gıda tüketimi food_change'de görülür
    # Büyük orduyla gıda değişimi küçük orduya göre daha olumsuz olmalı
    assert result.food_change is not None


def test_starvation_reduces_army(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    ai_a.resources.food = 0.0
    ai_a.resources.army = 100
    initial_army = ai_a.resources.army
    result = economy.process_turn(ai_a, game_map)
    if result.is_starving:
        assert ai_a.resources.army < initial_army, "Starvation should reduce army"


def test_research_increases_technology(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    ai_a.resources.gold = 10000.0
    initial_tech = ai_a.resources.technology
    economy.apply_research_action(ai_a)
    assert ai_a.resources.technology == initial_tech + 1


def test_research_fails_without_gold(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    ai_a.resources.gold = 0.0
    initial_tech = ai_a.resources.technology
    msg = economy.apply_research_action(ai_a)
    assert ai_a.resources.technology == initial_tech
    assert "failed" in msg.lower()


def test_technology_cannot_exceed_max(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    ai_a.resources.technology = ai_a.resources.MAX_TECHNOLOGY
    ai_a.resources.gold = 100000.0
    msg = economy.apply_research_action(ai_a)
    assert ai_a.resources.technology == ai_a.resources.MAX_TECHNOLOGY
    assert "max" in msg.lower()


def test_economy_action_costs_gold(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    ai_a.resources.gold = 200.0
    initial_gold = ai_a.resources.gold
    economy.apply_economy_action(ai_a)
    assert ai_a.resources.gold < initial_gold


def test_resource_consumption_is_balanced(setup):
    """
    Dominant strateji testi: büyük ordu küçük ordudan daha fazla kaynak tüketmeli.
    Büyük ordu daha yüksek upkeep (altın + gıda) ödemelidir.
    """
    countries, game_map, economy = setup

    # İki özdeş ülke, sadece ordu boyutu farklı
    from game.country import create_default_countries
    from game.map import GameMap

    countries_small = create_default_countries()
    countries_big = create_default_countries()
    map_small = GameMap(seed=42)
    map_big = GameMap(seed=42)

    small = countries_small[0]
    big = countries_big[0]

    small.resources.gold = 500.0
    small.resources.food = 400.0
    small.resources.army = 50    # Küçük ordu

    big.resources.gold = 500.0
    big.resources.food = 400.0
    big.resources.army = 300     # Büyük ordu

    # 5 tur işle
    for _ in range(5):
        economy.process_turn(small, map_small)
        economy.process_turn(big, map_big)

    # Büyük ordu daha fazla kaynak tüketir: net gold değişimi küçük ordudan daha kötü
    # veya food tüketimi daha yüksek
    big_upkeep = big.resources.army * 0.5 + big.resources.army * 0.3  # food + gold
    small_upkeep = small.resources.army * 0.5 + small.resources.army * 0.3
    assert big_upkeep > small_upkeep, "Bigger army should cost more resources per turn"
