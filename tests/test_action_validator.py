"""
test_action_validator.py — AI response parser ve validator testleri
"""
import pytest
from ai.response_parser import ResponseParser, AIDecision
from ai.action_validator import ActionValidator
from game.country import create_default_countries
from game.diplomacy import DiplomacySystem
from game.map import GameMap


@pytest.fixture
def setup():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)
    diplomacy = DiplomacySystem([c.agent_id for c in countries])
    return countries, game_map, diplomacy, ResponseParser(), ActionValidator()


def test_valid_json_parsed(setup):
    _, _, _, parser, _ = setup
    raw = '{"action": "ATTACK", "target": "AI_B", "reason": "Test"}'
    result = parser.parse(raw)
    assert result.is_valid
    assert result.decision.action == "ATTACK"
    assert result.decision.target == "AI_B"


def test_invalid_json_falls_back(setup):
    _, _, _, parser, _ = setup
    raw = "This is not JSON at all"
    result = parser.parse(raw)
    assert result.used_fallback
    assert result.decision.action == "DEFEND"


def test_unknown_action_falls_back(setup):
    _, _, _, parser, _ = setup
    raw = '{"action": "NUKE", "target": "AI_B"}'
    result = parser.parse(raw)
    assert result.used_fallback


def test_missing_action_falls_back(setup):
    _, _, _, parser, _ = setup
    raw = '{"target": "AI_B", "reason": "test"}'
    result = parser.parse(raw)
    assert result.used_fallback


def test_attack_nonexistent_target_rejected(setup):
    countries, game_map, diplomacy, _, validator = setup
    ai_a = countries[0]
    decision = AIDecision(action="ATTACK", target="AI_Z")
    result = validator.validate(decision, ai_a, countries, game_map, diplomacy)
    assert not result.is_valid


def test_attack_with_no_army_rejected(setup):
    countries, game_map, diplomacy, _, validator = setup
    ai_a = countries[0]
    ai_a.resources.army = 0
    decision = AIDecision(action="ATTACK", target="AI_B")
    result = validator.validate(decision, ai_a, countries, game_map, diplomacy)
    assert not result.is_valid


def test_research_without_gold_rejected(setup):
    countries, game_map, diplomacy, _, validator = setup
    ai_a = countries[0]
    ai_a.resources.gold = 0.0
    decision = AIDecision(action="RESEARCH")
    result = validator.validate(decision, ai_a, countries, game_map, diplomacy)
    assert not result.is_valid


def test_defend_always_valid(setup):
    countries, game_map, diplomacy, _, validator = setup
    ai_a = countries[0]
    ai_a.resources.army = 0
    ai_a.resources.gold = 0.0
    decision = AIDecision(action="DEFEND")
    result = validator.validate(decision, ai_a, countries, game_map, diplomacy)
    assert result.is_valid


def test_json_in_markdown_block_parsed(setup):
    _, _, _, parser, _ = setup
    raw = """Here is my decision:
```json
{"action": "ECONOMY", "target": null, "reason": "Need gold"}
```"""
    result = parser.parse(raw)
    assert result.is_valid
    assert result.decision.action == "ECONOMY"


def test_diplomacy_without_subaction_rejected(setup):
    countries, game_map, diplomacy, _, validator = setup
    ai_a = countries[0]
    decision = AIDecision(action="DIPLOMACY", target="AI_B", sub_action=None)
    result = validator.validate(decision, ai_a, countries, game_map, diplomacy)
    assert not result.is_valid
