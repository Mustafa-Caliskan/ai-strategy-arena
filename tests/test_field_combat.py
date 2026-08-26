"""
test_field_combat.py — Saha Çatışmaları, Split, Merge ve Kuşatma (Siege) Testleri
"""
import pytest
from game.country import create_default_countries
from game.map import GameMap, TileType
from game.combat import CombatSystem
from game.entities import ArmyEntity, EntityManager, ArmyStatus


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    combat = CombatSystem()
    manager = EntityManager()
    return countries, game_map, combat, manager


def test_army_split_and_merge(setup):
    countries, game_map, _, manager = setup
    ai_a = countries[0]
    
    # 50 askerlik ana ordu
    parent = manager.spawn_army(ai_a.agent_id, x=5, y=5, size=50, turn=1)
    
    # 20 askeri ayır (split)
    child = manager.split_army(parent.id, amount=20, turn=1)
    assert child is not None
    assert parent.size == 30
    assert child.size == 20
    assert (child.x, child.y) == (5, 5)
    
    # Aynı karedeki orduları birleştir (merge)
    manager.merge_same_owner_armies(turn=1)
    armies_at_tile = [a for a in manager.get_armies_for(ai_a.agent_id) if (a.x, a.y) == (5, 5)]
    assert len(armies_at_tile) == 1
    assert armies_at_tile[0].size == 50


def test_resolve_unit_clash_reduces_sizes(setup):
    countries, game_map, combat, manager = setup
    ai_a, ai_b = countries[0], countries[1]
    
    army_a = manager.spawn_army(ai_a.agent_id, x=10, y=10, size=60, turn=1)
    army_b = manager.spawn_army(ai_b.agent_id, x=10, y=10, size=20, turn=1)
    tile = game_map.get_tile(10, 10)
    
    res = combat.resolve_unit_clash(army_a, army_b, tile, tech_a=1, tech_b=1, game_map=game_map)
    assert res["winner_id"] == ai_a.agent_id
    assert army_a.size < 60
    assert army_b.size < 20


def test_resolve_city_siege_captures_city(setup):
    countries, game_map, combat, manager = setup
    ai_a, ai_b = countries[0], countries[1]
    
    # Şehir karesi hazırla
    city_tile = game_map.get_tile(ai_b.capital_x, ai_b.capital_y)
    city_tile.tile_type = TileType.CITY
    city_tile.owner = ai_b.agent_id
    ai_b.garrison_army = 15  # Zayıf garnizon
    
    # Güçlü taarruz ordusu
    attacking_army = manager.spawn_army(ai_a.agent_id, x=city_tile.x, y=city_tile.y, size=80, turn=1)
    
    res = combat.resolve_city_siege(
        attacking_army, ai_b, city_tile, tech_att=2, tech_def=1, game_map=game_map
    )
    
    assert res["att_won"] is True
    assert ai_b.garrison_army < 15
