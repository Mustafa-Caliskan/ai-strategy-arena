"""
openai_provider.py — OpenAI GPT provider
"""
from __future__ import annotations
import logging
from openai import AsyncOpenAI
from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(AIProvider):
    """
    OpenAI API entegrasyonu.
    """

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.3,
    ):
        super().__init__(agent_id, model, temperature)
        self._client = AsyncOpenAI(api_key=api_key)

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        self._call_count += 1
        logger.debug(f"[{self.agent_id}] OpenAI API call #{self._call_count}")

        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=256,
        )
        content = response.choices[0].message.content
        logger.debug(f"[{self.agent_id}] OpenAI response: {content[:100]}...")
        return content
