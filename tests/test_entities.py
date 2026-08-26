"""
test_entities.py — Fiziksel Varlık Sistemi (Pathfinding, ArmyEntity, EnvoyEntity, EntityManager) Testleri
"""
import pytest
from game.country import create_default_countries
from game.map import GameMap, TileType
from game.pathfinding import find_path
from game.entities import ArmyEntity, EnvoyEntity, EntityManager, ArmyStatus, EnvoyStatus


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    entity_manager = EntityManager()
    return countries, game_map, entity_manager


def test_pathfinding_finds_valid_path(setup):
    _, game_map, _ = setup
    start = (2, 10)
    goal = (5, 10)
    path = find_path(game_map, start, goal)
    
    assert len(path) > 0
    assert path[-1] == goal
    assert start not in path


def test_army_entity_spawn_and_movement(setup):
    countries, game_map, entity_manager = setup
    ai_a = countries[0]
    
    army = entity_manager.spawn_army(ai_a.agent_id, x=2, y=10, size=40, turn=1)
    assert army.id.startswith("ARMY_AI_A")
    assert army.size == 40
    assert army.status == ArmyStatus.IDLE
    
    # Hedef belirle
    success = army.set_target(dest_x=4, dest_y=10, game_map=game_map)
    assert success
    assert army.status == ArmyStatus.MOVING
    assert len(army.path) == 2
    
    # 1 adım at
    army.step(game_map)
    assert (army.x, army.y) == (3, 10)
    assert army.status == ArmyStatus.MOVING
    
    # 2. adım at -> hedefe varış
    army.step(game_map)
    assert (army.x, army.y) == (4, 10)
    assert army.status == ArmyStatus.IDLE


def test_envoy_entity_dispatch_and_delivery(setup):
    countries, game_map, entity_manager = setup
    ai_a, ai_b = countries
    
    envoy = entity_manager.dispatch_envoy(
        owner=ai_a.agent_id,
        target_agent_id=ai_b.agent_id,
        start_x=2,
        start_y=10,
        dest_x=4,
        dest_y=10,
        message="Peace offer from the West.",
        contract_data=None,
        turn=1,
        game_map=game_map,
    )
    
    assert envoy.status == EnvoyStatus.TRAVELING
    assert len(envoy.path) == 2
    
    # Elçi hızı 2 olduğu için 1 turda 2 kare gidip varış yapar
    entity_manager.step_all(game_map, current_turn=2, countries=countries)
    
    # Mesaj AI_B'nin gelen kutusuna ulaşmış olmalı
    assert len(ai_b.diplomatic_inbox) == 1
    assert ai_b.diplomatic_inbox[0]["from"] == "AI_A"
    assert "Peace offer" in ai_b.diplomatic_inbox[0]["message"]
