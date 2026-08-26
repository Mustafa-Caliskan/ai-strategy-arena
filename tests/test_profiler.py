"""
test_profiler.py — 6 Boyutlu Davranış Radarı ve Karakter Profilleme Testleri
"""
import pytest
from game.country import Country
from simulation.event_system import GameEvent
from benchmark.behavioral_profiler import BehavioralProfiler, BehavioralDimensions


@pytest.fixture
def profiler():
    return BehavioralProfiler()


def test_aggressive_agent_profiling(profiler):
    country = Country(agent_id="AI_Warmonger", name="War Empire", color=(220, 50, 50))
    country.turns_survived = 20
    country.total_attacks = 15
    country.total_betrayals = 2
    
    events = [
        GameEvent(turn=i, agent_id="AI_Warmonger", action="ATTACK", target="AI_B", sub_action=None, result="Won")
        for i in range(1, 15)
    ]
    events.extend([
        GameEvent(turn=i, agent_id="AI_Warmonger", action="RECRUIT", target=None, sub_action=None, result="Recruited")
        for i in range(15, 20)
    ])
    
    profile = profiler.analyze(country, events, total_turns=20, model_name="test-warmonger")
    
    assert profile.dimensions.aggressiveness > 60.0
    assert profile.dimensions.trustworthiness < 50.0
    assert profile.dimensions.deception_index > 40.0
    assert "Warmonger" in profile.archetype or "Instigator" in profile.archetype
    
    radar = profile.generate_ascii_radar()
    assert "STRATEGIC RADAR PROFILE" in radar
    assert "[AGG]" in radar


def test_economic_builder_profiling(profiler):
    country = Country(agent_id="AI_Builder", name="Trade Empire", color=(50, 200, 50))
    country.turns_survived = 20
    country.total_trades = 5
    country.total_alliances = 2
    country.total_betrayals = 0
    country.resources.technology = 4
    
    events = [
        GameEvent(turn=i, agent_id="AI_Builder", action="BUILD", target=None, sub_action="FARM", result="Built")
        for i in range(1, 10)
    ]
    events.extend([
        GameEvent(turn=i, agent_id="AI_Builder", action="TRADE", target="AI_B", sub_action=None, result="Traded")
        for i in range(10, 16)
    ])
    events.extend([
        GameEvent(turn=i, agent_id="AI_Builder", action="RESEARCH", target=None, sub_action=None, result="Researched")
        for i in range(16, 20)
    ])
    
    profile = profiler.analyze(country, events, total_turns=20, model_name="test-builder")
    
    assert profile.dimensions.economic_focus > 50.0
    assert profile.dimensions.trustworthiness >= 70.0
    assert profile.dimensions.deception_index == 0.0
    assert profile.dimensions.long_term_planning > 50.0
