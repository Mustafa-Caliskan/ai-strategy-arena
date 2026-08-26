"""
test_buildings.py — WorldBox binaları ve Catan çoklu kaynak testleri
"""
import pytest
from game.country import create_default_countries
from game.map import GameMap, TileType
from game.economy import EconomySystem
from game.buildings import BuildingType, Building


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)
    economy = EconomySystem()
    return countries, game_map, economy


def test_initial_multi_resources(setup):
    countries, _, _ = setup
    ai_a = countries[0]
    r = ai_a.resources
    assert r.wood > 0
    assert r.stone > 0
    assert r.iron > 0
    assert r.influence > 0


def test_build_farm_increases_food_yield(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    initial_food = ai_a.resources.food
    
    # Çiftlik inşa et
    msg = economy.apply_build_action(ai_a, game_map, "FARM")
    assert "constructed FARM" in msg
    
    # 1 tur işle
    res = economy.process_turn(ai_a, game_map)
    assert res.food_change > 0


def test_build_lumber_mill_and_mine(setup):
    countries, game_map, economy = setup
    ai_a = countries[0]
    
    ai_a.resources.gold = 500.0
    ai_a.resources.wood = 500.0
    ai_a.resources.stone = 500.0
    ai_a.resources.iron = 500.0
    
    msg_mill = economy.apply_build_action(ai_a, game_map, "LUMBER_MILL")
    assert "constructed LUMBER_MILL" in msg_mill
    
    msg_mine = economy.apply_build_action(ai_a, game_map, "MINE")
    assert "constructed MINE" in msg_mine


def test_recruit_action_requires_iron_and_gold(setup):
    countries, _, economy = setup
    ai_a = countries[0]
    
    ai_a.resources.gold = 100.0
    ai_a.resources.iron = 0.0
    msg_fail = economy.apply_recruit_action(ai_a, amount=20)
    assert "failed" in msg_fail.lower()
    
    ai_a.resources.iron = 50.0
    msg_ok = economy.apply_recruit_action(ai_a, amount=20)
    assert "recruited" in msg_ok.lower()
    assert ai_a.resources.army == 100


def test_fort_increases_defense_bonus(setup):
    _, game_map, _ = setup
    tile = game_map.get_tile(2, 2)
    base_def = tile.get_defense_bonus()
    
    game_map.build_structure(2, 2, BuildingType.FORT)
    fort_def = tile.get_defense_bonus()
    assert fort_def > base_def
