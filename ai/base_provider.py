"""
base_provider.py — AIProvider abstract sınıfı
Tüm LLM sağlayıcıları bu sınıftan türer.
"""
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """
    Tüm AI model sağlayıcılarının uymak zorunda olduğu arayüz.
    Oyun kodu yalnızca bu sınıfla konuşur.
    """

    def __init__(self, agent_id: str, model_name: str, temperature: float = 0.3):
        self.agent_id = agent_id
        self.model_name = model_name
        self.temperature = temperature
        self._call_count = 0
        self._fallback_count = 0

    @abstractmethod
    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        """
        LLM'e gönder, ham string cevabı döndür.
        Hata durumunda exception fırlat (orchestrator yakalar).
        """
        ...

    def decide(self, system_prompt: str, user_prompt: str) -> str:
        """Sync wrapper — test ve headless modda kullanılır."""
        return asyncio.run(self.decide_async(system_prompt, user_prompt))

    @property
    def provider_name(self) -> str:
        return self.__class__.__name__.replace("Provider", "").upper()

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "provider": self.provider_name,
            "model": self.model_name,
            "calls": self._call_count,
            "fallbacks": self._fallback_count,
        }

    def __repr__(self) -> str:
        return f"{self.provider_name}({self.agent_id}, {self.model_name})"
