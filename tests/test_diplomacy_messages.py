"""
test_diplomacy_messages.py — LLM-to-LLM Diplomasi & Elçi Mesajlaşma Testleri
"""
import pytest
from ai.response_parser import ResponseParser, AIDecision
from game.country import create_default_countries
from game.diplomacy import DiplomacySystem
from game.game_state import GameStateBuilder
from game.map import GameMap
from simulation.turn_manager import TurnManager
from ai.base_provider import AIProvider
import json


def test_ai_decision_parses_diplomatic_message():
    parser = ResponseParser()
    raw = json.dumps({
        "action": "DIPLOMACY",
        "target": "AI_B",
        "sub_action": "ALLIANCE",
        "diplomatic_message": "Let us unite against all odds.",
        "reason": "Alliance is mutually beneficial."
    })
    result = parser.parse(raw)
    assert result.is_valid
    assert result.decision.action == "DIPLOMACY"
    assert result.decision.target == "AI_B"
    assert result.decision.sub_action == "ALLIANCE"
    assert result.decision.diplomatic_message == "Let us unite against all odds."


def test_country_receives_diplomatic_message():
    countries = create_default_countries()
    ai_a, ai_b = countries
    
    assert len(ai_b.diplomatic_inbox) == 0
    ai_b.receive_message(from_agent=ai_a.agent_id, message="Peace offer from Alpha.", turn=1)
    
    assert len(ai_b.diplomatic_inbox) == 1
    assert ai_b.diplomatic_inbox[0]["from"] == "AI_A"
    assert ai_b.diplomatic_inbox[0]["message"] == "Peace offer from Alpha."
    assert ai_b.diplomatic_inbox[0]["turn"] == 1
    assert ai_b.total_messages_received == 1


def test_game_state_includes_diplomatic_inbox():
    countries = create_default_countries()
    ai_a, ai_b = countries
    game_map = GameMap(seed=42)
    diplomacy = DiplomacySystem([c.agent_id for c in countries])
    builder = GameStateBuilder()
    
    ai_a.receive_message(from_agent="AI_B", message="Trade proposal", turn=3)
    
    state = builder.build(
        turn=4,
        perspective_agent=ai_a,
        all_countries=countries,
        game_map=game_map,
        diplomacy=diplomacy,
    )
    
    assert "diplomatic_inbox" in state
    assert len(state["diplomatic_inbox"]) == 1
    assert state["diplomatic_inbox"][0]["from"] == "AI_B"
    assert state["diplomatic_inbox"][0]["message"] == "Trade proposal"


def test_turn_manager_delivers_diplomatic_message():
    countries = create_default_countries()
    game_map = GameMap(seed=42)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)
        
    class MessengerProvider(AIProvider):
        def __init__(self, agent_id: str):
            super().__init__(agent_id, "messenger", 0.0)
        async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
            if self.agent_id == "AI_A":
                return json.dumps({
                    "action": "DIPLOMACY",
                    "target": "AI_B",
                    "sub_action": "TRADE",
                    "diplomatic_message": "Greetings Beta, accept our trade convoy.",
                    "reason": "Economic expansion"
                })
            else:
                return json.dumps({
                    "action": "ECONOMY",
                    "target": None,
                    "reason": "Building infrastructure"
                })

    providers = {
        "AI_A": MessengerProvider("AI_A"),
        "AI_B": MessengerProvider("AI_B"),
    }

    manager = TurnManager(
        countries=countries,
        providers=providers,
        game_map=game_map,
        max_turns=3,
        seed=42,
    )

    manager.run_game_sync()
    
    ai_b = manager._find_country("AI_B", manager.countries)
    ai_a = manager._find_country("AI_A", manager.countries)
    
    # AI_B should have received messages from AI_A
    assert len(ai_b.diplomatic_inbox) >= 1
    assert ai_b.diplomatic_inbox[0]["from"] == "AI_A"
    assert "convoy" in ai_b.diplomatic_inbox[0]["message"].lower()
    assert ai_a.total_messages_sent >= 1
