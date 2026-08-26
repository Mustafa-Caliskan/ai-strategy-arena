"""
anthropic_provider.py — Anthropic Claude provider (Stub - Faz 3+)
"""
from __future__ import annotations
from ai.base_provider import AIProvider


class AnthropicProvider(AIProvider):
    def __init__(self, agent_id: str, api_key: str, model: str = "claude-3-5-haiku-20241022", temperature: float = 0.3):
        super().__init__(agent_id, model, temperature)
        self._api_key = api_key

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic
        self._call_count += 1
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        message = await client.messages.create(
            model=self.model_name,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
