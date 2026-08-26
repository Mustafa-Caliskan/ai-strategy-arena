"""
test_contracts.py — Resmi Sözleşmeler (Contracts), Paktlar ve İhanet Takip Testleri
"""
import pytest
from game.country import create_default_countries
from game.diplomacy import DiplomacySystem
from game.contracts import ContractManager, ContractType, ContractStatus


@pytest.fixture
def setup():
    countries = create_default_countries()
    diplomacy = DiplomacySystem([c.agent_id for c in countries])
    return countries, diplomacy


def test_propose_and_accept_contract(setup):
    _, diplomacy = setup
    manager = diplomacy.contracts
    
    contract = manager.propose_contract(
        initiator="AI_A",
        target="AI_B",
        contract_type=ContractType.NON_AGGRESSION,
        duration=5,
        turn=1,
    )
    assert contract.status == ContractStatus.PROPOSED
    assert contract.turns_remaining == 5
    
    accepted = manager.accept_contract(contract.contract_id, turn=1)
    assert accepted is not None
    assert accepted.status == ContractStatus.ACTIVE
    assert manager.has_non_aggression_pact("AI_A", "AI_B") is not None


def test_contract_fulfilled_after_duration(setup):
    _, diplomacy = setup
    manager = diplomacy.contracts
    
    contract = manager.propose_contract(
        initiator="AI_A",
        target="AI_B",
        contract_type=ContractType.NON_AGGRESSION,
        duration=3,
        turn=1,
    )
    manager.accept_contract(contract.contract_id, turn=1)
    
    # 3 tur ilerlet
    for t in range(2, 5):
        events = manager.tick_all(current_turn=t)
    
    assert contract.status == ContractStatus.FULFILLED
    assert manager.has_non_aggression_pact("AI_A", "AI_B") is None
    assert manager.total_contracts_fulfilled == 1


def test_betrayal_detected_when_attacking_during_pact(setup):
    countries, diplomacy = setup
    ai_a, ai_b = countries
    manager = diplomacy.contracts
    
    # Pakt oluştur ve imzala
    contract = manager.propose_contract(
        initiator="AI_A",
        target="AI_B",
        contract_type=ContractType.NON_AGGRESSION,
        duration=10,
        turn=1,
    )
    manager.accept_contract(contract.contract_id, turn=1)
    
    # AI_A, pakt sürerken AI_B'ye savaş açıyor (İHANET)
    msg = diplomacy.apply_declare_war(ai_a, ai_b, turn=2)
    assert "BETRAYAL" in msg
    assert contract.status == ContractStatus.VIOLATED
    assert contract.violated_by == "AI_A"
    assert ai_a.total_betrayals == 1
