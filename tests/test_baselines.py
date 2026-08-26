"""
test_baselines.py — Baseline Botların Karar ve Uyumluluk Testleri
"""
import pytest
import json
from game.country import create_default_countries
from game.map import GameMap
from game.diplomacy import DiplomacySystem
from game.game_state import GameStateBuilder
from ai.response_parser import ResponseParser
from ai.action_validator import ActionValidator
from ai.baseline_agents import GreedyProvider, DefensiveProvider, EconomicProvider, RandomProvider


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    diplomacy = DiplomacySystem([c.agent_id for c in countries])
    state_builder = GameStateBuilder()
    parser = ResponseParser()
    validator = ActionValidator()
    
    state = state_builder.build(
        turn=5,
        perspective_agent=countries[0],
        all_countries=countries,
        game_map=game_map,
        diplomacy=diplomacy,
    )
    user_prompt = json.dumps(state)
    return countries, game_map, diplomacy, parser, validator, user_prompt


def test_greedy_agent_decides_valid_action(setup):
    countries, game_map, diplomacy, parser, validator, user_prompt = setup
    bot = GreedyProvider(agent_id=countries[0].agent_id, seed=42)
    
    raw = bot.decide("", user_prompt)
    parsed = parser.parse(raw)
    assert parsed.is_valid
    
    val = validator.validate(parsed.decision, countries[0], countries, game_map, diplomacy)
    assert val.is_valid


def test_defensive_agent_decides_valid_action(setup):
    countries, game_map, diplomacy, parser, validator, user_prompt = setup
    bot = DefensiveProvider(agent_id=countries[0].agent_id, seed=42)
    
    raw = bot.decide("", user_prompt)
    parsed = parser.parse(raw)
    assert parsed.is_valid
    
    val = validator.validate(parsed.decision, countries[0], countries, game_map, diplomacy)
    assert val.is_valid


def test_economic_agent_decides_valid_action(setup):
    countries, game_map, diplomacy, parser, validator, user_prompt = setup
    bot = EconomicProvider(agent_id=countries[0].agent_id, seed=42)
    
    raw = bot.decide("", user_prompt)
    parsed = parser.parse(raw)
    assert parsed.is_valid
    
    val = validator.validate(parsed.decision, countries[0], countries, game_map, diplomacy)
    assert val.is_valid
