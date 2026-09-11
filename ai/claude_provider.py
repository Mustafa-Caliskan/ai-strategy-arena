"""
claude_provider.py — Anthropic Claude API Provider for AI Strategy Arena
Dedicated provider for evaluating Anthropic Claude models (Claude 3.7 / 3.5 Sonnet / Haiku / Opus)
in multi-agent grand strategy environments.

Research & Benchmark Focus:
- Long-Term Strategic Planning (LTP): Multi-turn infrastructural capital, technology tree progression, and siege defense.
- Asymmetric Diplomacy (ADP): Covert information management under Fog of War, strategic bluffing, and envoy diplomacy.
- Treaty Fidelity & Betrayal Dynamics (TRU & DEC): Evaluating game-theoretic loyalty, pact adherence, and opportunistic breach thresholds.
"""
from __future__ import annotations
import os
import logging
from typing import Optional, Dict, Any

from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)

# Default model: Claude Sonnet 5 (customizable via ANTHROPIC_MODEL environment variable)
DEFAULT_CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")


class ClaudeProvider(AIProvider):
    """
    Anthropic Claude API Provider implementation for AI Strategy Arena.
    Designed for frontier multi-agent strategy, diplomatic negotiations,
    and game-theoretic decision benchmarks.
    """

    def __init__(
        self,
        agent_id: str,
        api_key: Optional[str] = None,
        model: str = DEFAULT_CLAUDE_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 1500,
        enable_extended_thinking: bool = False,
        thinking_budget_tokens: int = 1024,
    ):
        super().__init__(agent_id, model, temperature)
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY", "")
        if not self.api_key:
            logger.warning(
                f"[{agent_id}] ANTHROPIC_API_KEY is not set. ClaudeProvider will require an explicit key."
            )

        self.max_tokens = max_tokens
        self.enable_extended_thinking = enable_extended_thinking
        self.thinking_budget_tokens = thinking_budget_tokens
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package is required for ClaudeProvider. Install via: pip install anthropic"
                )
        return self._client

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        """
        Executes an asynchronous decision call to the Anthropic Claude API.
        Extracts strategic thought, diplomatic letters, and validated JSON action plans.
        """
        self._call_count += 1
        logger.info(f"[{self.agent_id}] Calling Claude ({self.model_name}) | Turn Call #{self._call_count}")

        client = self._get_client()

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }

        # Extended thinking configuration
        if self.enable_extended_thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget_tokens
            }

        try:
            response = await client.messages.create(**kwargs)
            
            # Extract final text block from response (handling thinking blocks if present)
            content_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    content_text += block.text
                elif hasattr(block, "text") and getattr(block, "type", None) != "thinking":
                    content_text += block.text

            # Fallback if no text block was found
            if not content_text and response.content:
                content_text = str(response.content[0])

            logger.debug(f"[{self.agent_id}] Claude response received ({len(content_text)} chars)")
            return content_text

        except Exception as e:
            self._fallback_count += 1
            logger.error(f"[{self.agent_id}] Claude API error: {e}", exc_info=True)
            raise e


# Backward compatibility alias
AnthropicProvider = ClaudeProvider
