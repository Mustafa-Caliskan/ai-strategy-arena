"""
test_diplomacy.py — Diplomasi sistemi testleri
"""
import pytest
from game.country import create_default_countries
from game.diplomacy import DiplomacySystem, DiplomaticStatus


@pytest.fixture
def setup():
    countries = create_default_countries()
    diplomacy = DiplomacySystem([c.agent_id for c in countries])
    return countries, diplomacy


def test_initial_state_is_neutral(setup):
    countries, diplomacy = setup
    rel = diplomacy.get_relation("AI_A", "AI_B")
    assert rel.status == DiplomaticStatus.NEUTRAL
    assert rel.score == 0.0


def test_declare_war(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    msg = diplomacy.apply_declare_war(ai_a, ai_b)
    assert diplomacy.is_at_war("AI_A", "AI_B")
    assert "WAR" in msg.upper() or "war" in msg.lower()


def test_peace_after_war(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    diplomacy.apply_declare_war(ai_a, ai_b)
    assert diplomacy.is_at_war("AI_A", "AI_B")
    diplomacy.apply_peace(ai_a, ai_b)
    assert not diplomacy.is_at_war("AI_A", "AI_B")


def test_trade_increases_gold(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    ai_a.resources.gold = 100.0
    ai_b.resources.gold = 100.0
    diplomacy.apply_trade(ai_a, ai_b)
    assert ai_a.resources.gold > 100.0
    assert ai_b.resources.gold > 100.0


def test_cannot_trade_during_war(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    diplomacy.apply_declare_war(ai_a, ai_b)
    msg = diplomacy.apply_trade(ai_a, ai_b)
    assert "war" in msg.lower() or "cannot" in msg.lower()


def test_alliance_requires_positive_relation(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    # Düşük skor ile ittifak reddedilmeli
    rel = diplomacy.get_relation("AI_A", "AI_B")
    rel.score = 10.0
    msg = diplomacy.apply_alliance(ai_a, ai_b)
    assert "rejected" in msg.lower() or "too low" in msg.lower()


def test_alliance_with_good_relation(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    rel = diplomacy.get_relation("AI_A", "AI_B")
    rel.score = 50.0
    msg = diplomacy.apply_alliance(ai_a, ai_b)
    assert diplomacy.is_allied("AI_A", "AI_B")


def test_betrayal_tracked(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    rel = diplomacy.get_relation("AI_A", "AI_B")
    rel.score = 50.0
    diplomacy.apply_alliance(ai_a, ai_b)
    diplomacy.apply_declare_war(ai_a, ai_b)
    assert ai_a.total_betrayals == 1


def test_tick_worsens_war_score(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    diplomacy.apply_declare_war(ai_a, ai_b)
    initial_score = diplomacy.get_score("AI_A", "AI_B")
    for _ in range(5):
        diplomacy.tick_all()
    assert diplomacy.get_score("AI_A", "AI_B") < initial_score
