"""
deepseek_provider.py — DeepSeek AI provider
DeepSeek, OpenAI-compatible API kullanır.
Base URL: https://api.deepseek.com
"""
from __future__ import annotations
import logging
import os
from openai import AsyncOpenAI
from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")   # deepseek-chat / DeepSeek V4 Flash


class DeepSeekProvider(AIProvider):
    """
    DeepSeek API entegrasyonu.
    OpenAI SDK ile çalışır, sadece base_url ve api_key farklı.
    """

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.3,
    ):
        super().__init__(agent_id, model, temperature)
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
        )

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        self._call_count += 1
        logger.debug(f"[{self.agent_id}] DeepSeek API call #{self._call_count}")

        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=1024,
        )
        content = response.choices[0].message.content
        logger.debug(f"[{self.agent_id}] DeepSeek response: {content[:100]}...")
        return content
