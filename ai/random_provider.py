"""
random_provider.py — Test AI
API çağrısı yapmaz, rastgele legal action seçer.
Faz 1 ve Faz 2 testleri için kullanılır.
"""
from __future__ import annotations
import json
import random
from ai.base_provider import AIProvider


class RandomProvider(AIProvider):
    """
    API gerektirmeyen sahte AI.
    Verilen action listesinden rastgele bir eylem seçer.
    Her zaman geçerli JSON döndürür.
    """

    def __init__(self, agent_id: str, seed: int | None = None):
        super().__init__(agent_id, model_name="random-v1", temperature=1.0)
        self._rng = random.Random(seed)

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        """
        user_prompt içindeki JSON'dan available_actions'ı parse et,
        rastgele seç ve geçerli JSON response döndür.
        """
        # user_prompt'ta game_state JSON var
        try:
            import re
            # JSON bloğu bul
            json_match = re.search(r'\{.*\}', user_prompt, re.DOTALL)
            if json_match:
                state = json.loads(json_match.group())
                actions = state.get("available_actions", ["DEFEND"])
                other_players = state.get("other_players", [])
            else:
                actions = ["DEFEND"]
                other_players = []
        except Exception:
            actions = ["DEFEND"]
            other_players = []

        action = self._rng.choice(actions)

        # Target seçimi (ATTACK, TRADE, DIPLOMACY için)
        target = None
        if other_players:
            target = self._rng.choice(other_players)["id"]

        response = {"action": action, "reason": "Random selection for testing."}
        if action in ("ATTACK", "TRADE", "DIPLOMACY") and target:
            response["target"] = target
        if action == "DIPLOMACY" and target:
            response["sub_action"] = self._rng.choice(["PEACE", "TRADE", "ALLIANCE"])

        self._call_count += 1
        return json.dumps(response)
