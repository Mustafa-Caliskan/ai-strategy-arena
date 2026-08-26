"""
baseline_agents.py — Standart Kural Tabanlı Baseline Yapay Zeka Ajanları
Greedy (Saldırgan/Askeri), Defensive (Savunmacı/Barışçıl), Economic (Tüccar/İnşaatçı) ve Random.
API maliyeti olmadan deterministik benchmark testleri için kullanılır.
"""
from __future__ import annotations
import json
import re
import random
from typing import Optional

from ai.base_provider import AIProvider
from ai.random_provider import RandomProvider


def _extract_state(user_prompt: str) -> dict:
    """Prompt içindeki game state JSON'ını güvenli şekilde ayıklar."""
    try:
        json_match = re.search(r'\{.*\}', user_prompt, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return {}


class GreedyProvider(AIProvider):
    """
    Saldırgan ve yayılmacı askeri bot.
    Öncelikler:
    1. Orduyu büyüt (RECRUIT)
    2. En zayıf komşuya saldır (ATTACK)
    3. Toprak fethet (EXPAND)
    4. Maden inşa et (BUILD MINE)
    """

    def __init__(self, agent_id: str, seed: Optional[int] = None):
        super().__init__(agent_id, model_name="baseline-greedy-v1", temperature=0.0)
        self._rng = random.Random(seed)

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        self._call_count += 1
        state = _extract_state(user_prompt)
        actions = set(state.get("available_actions", ["DEFEND"]))
        player = state.get("player", {})
        other_players = state.get("other_players", [])

        # 1. Asker bas
        if "RECRUIT" in actions and player.get("army", 0) < 140 and player.get("gold", 0) >= 40:
            return json.dumps({
                "action": "RECRUIT",
                "reason": "Greedy: Expanding military force."
            })

        # 2. En zayıf düşmanı bul ve saldır
        if "ATTACK" in actions and other_players:
            weakest = min(other_players, key=lambda p: p.get("known_army", 999))
            return json.dumps({
                "action": "ATTACK",
                "target": weakest["id"],
                "reason": f"Greedy: Striking weakest opponent ({weakest['id']}).",
                "diplomatic_message": "Surrender your lands or be crushed."
            })

        # 3. Genişle
        if "EXPAND" in actions and player.get("gold", 0) >= 40:
            return json.dumps({
                "action": "EXPAND",
                "reason": "Greedy: Expanding territorial borders."
            })

        # 4. Maden inşa et
        if "BUILD" in actions and player.get("wood", 0) >= 20 and player.get("stone", 0) >= 20:
            return json.dumps({
                "action": "BUILD",
                "sub_action": "MINE",
                "reason": "Greedy: Building iron/gold mine."
            })

        # 5. Ekonomi
        return json.dumps({
            "action": "ECONOMY",
            "reason": "Greedy: Gathering war funds."
        })


class DefensiveProvider(AIProvider):
    """
    Savunmacı ve barışçıl bot.
    Öncelikler:
    1. Savaşta ise barış teklif et veya DEFEND yap.
    2. Surları ve çiftlikleri geliştir (BUILD FORT / FARM).
    3. Saldırmazlık paktları ve ittifaklar ara.
    """

    def __init__(self, agent_id: str, seed: Optional[int] = None):
        super().__init__(agent_id, model_name="baseline-defensive-v1", temperature=0.0)
        self._rng = random.Random(seed)

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        self._call_count += 1
        state = _extract_state(user_prompt)
        actions = set(state.get("available_actions", ["DEFEND"]))
        player = state.get("player", {})
        other_players = state.get("other_players", [])

        # Savaşta olunan oyuncu var mı?
        hostile = [p for p in other_players if p.get("relation_status") == "war"]
        if hostile and "DIPLOMACY" in actions:
            return json.dumps({
                "action": "DIPLOMACY",
                "target": hostile[0]["id"],
                "sub_action": "PEACE",
                "reason": "Defensive: Offering peace to end hostility.",
                "diplomatic_message": "Let us cease bloodshed and restore peace."
            })

        if hostile and "DEFEND" in actions:
            return json.dumps({
                "action": "DEFEND",
                "reason": "Defensive: Fortifying borders against invasion."
            })

        # Kale veya Çiftlik inşa et
        if "BUILD" in actions:
            if player.get("stone", 0) >= 40 and player.get("wood", 0) >= 20:
                return json.dumps({
                    "action": "BUILD",
                    "sub_action": "FORT",
                    "reason": "Defensive: Building defensive fort."
                })
            elif player.get("wood", 0) >= 30:
                return json.dumps({
                    "action": "BUILD",
                    "sub_action": "FARM",
                    "reason": "Defensive: Securing food reserves."
                })

        # Pakt veya İttifak teklif et
        if "DIPLOMACY" in actions and other_players:
            target = other_players[0]["id"]
            return json.dumps({
                "action": "DIPLOMACY",
                "target": target,
                "sub_action": "ALLIANCE",
                "reason": "Defensive: Proposing mutual defense pact.",
                "diplomatic_message": "Our empires are stronger together."
            })

        return json.dumps({
            "action": "DEFEND",
            "reason": "Defensive: Guarding realm."
        })


class EconomicProvider(AIProvider):
    """
    Tüccar ve kalkınmacı bot.
    Öncelikler:
    1. Ticaret anlaşmaları yap (TRADE).
    2. Çiftlik, kereste, maden ve şehirler inşa et (BUILD).
    3. Teknoloji araştır (RESEARCH).
    """

    def __init__(self, agent_id: str, seed: Optional[int] = None):
        super().__init__(agent_id, model_name="baseline-economic-v1", temperature=0.0)
        self._rng = random.Random(seed)
        self._build_cycle = ["FARM", "LUMBER_MILL", "MINE", "CITY"]
        self._cycle_idx = 0

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        self._call_count += 1
        state = _extract_state(user_prompt)
        actions = set(state.get("available_actions", ["DEFEND"]))
        player = state.get("player", {})
        other_players = state.get("other_players", [])

        # 1. Ticaret kur
        neutral_players = [p for p in other_players if p.get("relation_status") != "war"]
        if "TRADE" in actions and neutral_players:
            target = neutral_players[0]["id"]
            return json.dumps({
                "action": "TRADE",
                "target": target,
                "reason": "Economic: Opening profitable trade route.",
                "diplomatic_message": "May our caravans bring prosperity to both realms."
            })

        # 2. Teknoloji araştır
        if "RESEARCH" in actions and player.get("gold", 0) >= 70:
            return json.dumps({
                "action": "RESEARCH",
                "reason": "Economic: Investing in scientific discovery."
            })

        # 3. Döngüsel Altyapı İnşaatı
        if "BUILD" in actions:
            sub = self._build_cycle[self._cycle_idx % len(self._build_cycle)]
            self._cycle_idx += 1
            return json.dumps({
                "action": "BUILD",
                "sub_action": sub,
                "reason": f"Economic: Infrastructure project ({sub})."
            })

        # 4. Toprak genişlemesi
        if "EXPAND" in actions and player.get("gold", 0) >= 40:
            return json.dumps({
                "action": "EXPAND",
                "reason": "Economic: Claiming fertile resource lands."
            })

        return json.dumps({
            "action": "ECONOMY",
            "reason": "Economic: Boosting municipal revenue."
        })
