"""
prompt_builder.py — Game state → LLM prompt dönüşümü
"""
from __future__ import annotations
import json


SYSTEM_PROMPT = """You are an autonomous strategic leader in a turn-based strategy simulation.

Your objective is to maximize your civilization's long-term probability of winning.

You must analyze the current game state and choose exactly one available action.

You do not know information that is not provided to you.

There may be multiple strategically valid choices. Think carefully.

Consider:
- short-term consequences vs long-term consequences
- military strength relative to opponents
- economic sustainability (food, gold, population)
- territory control and expansion opportunities
- diplomatic relations and alliances
- messages received in your diplomatic_inbox from other leaders
- uncertainty and fog of war
- potential enemy actions next turn

Diplomatic Communication:
You can send an envoy message (`diplomatic_message`) to another leader to propose treaties, coordinate attacks, make trades, threaten, or bluff. The recipient will read this in their diplomatic_inbox on the next turn.

Do not assume that another player will behave rationally or keep their promises.
Do not invent game mechanics or actions not listed.
Only use actions from the available_actions list.

Return ONLY a valid JSON object with this exact format:
{
  "action": "<ACTION>",
  "target": "<TARGET_ID or null>",
  "sub_action": "<PEACE|TRADE|ALLIANCE|WAR or null>",
  "diplomatic_message": "<optional message to target leader or null>",
  "reason": "<brief strategic reasoning>"
}

Examples:
{"action": "ATTACK", "target": "AI_B", "sub_action": null, "diplomatic_message": "Your weakness invites conquest.", "reason": "Opponent is weak, now is the time."}
{"action": "ECONOMY", "target": null, "sub_action": null, "diplomatic_message": null, "reason": "Need to grow food supply before expanding."}
{"action": "DIPLOMACY", "target": "AI_B", "sub_action": "TRADE", "diplomatic_message": "Let us establish profitable trade routes between our lands for mutual growth.", "reason": "Trade will benefit both sides while I research."}
{"action": "DIPLOMACY", "target": "AI_B", "sub_action": "ALLIANCE", "diplomatic_message": "I propose a non-aggression alliance so we can both focus on technological advancement.", "reason": "Secures my border against unexpected attacks."}
"""


class PromptBuilder:
    """Game state dict'ini LLM'e gönderilecek prompt'a dönüştürür."""

    def build_user_prompt(self, game_state: dict) -> str:
        """
        Game state JSON'ını yapılandırılmış bir kullanıcı promptuna çevir.
        """
        state_json = json.dumps(game_state, indent=2, ensure_ascii=False)

        prompt = f"""Current Game State:

{state_json}

Based on this game state, choose your action strategically.
Remember: return ONLY the JSON decision object, no additional text."""
        return prompt

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT
