"""
backend/ai/llm_bridge.py
Async multi-provider LLM köprüsü (OpenAI, DeepSeek, Baseline AI).
Robust JSON parsing ve hata toleransı.
"""
from __future__ import annotations
import os
import json
import time
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class LLMBridge:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("CLAUDE_API_KEY", "")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

        self._openai_client = None
        self._deepseek_client = None
        self._anthropic_client = None

        if len(self.openai_key) > 10:
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=self.openai_key)
            except Exception as e:
                print(f"[LLM] OpenAI init error: {e}")

        if len(self.deepseek_key) > 10:
            try:
                from openai import AsyncOpenAI
                self._deepseek_client = AsyncOpenAI(
                    api_key=self.deepseek_key,
                    base_url="https://api.deepseek.com"
                )
            except Exception as e:
                print(f"[LLM] DeepSeek init error: {e}")

        if len(self.anthropic_key) > 10:
            try:
                import anthropic
                self._anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
            except Exception as e:
                print(f"[LLM] Anthropic init error: {e}")

    async def get_decision(
        self,
        provider_name: str,
        system_prompt: str,
        user_prompt: str,
        fallback_role: str = "balanced"
    ) -> Dict[str, Any]:
        """Modelden asenkron karar alır ve temiz JSON döndürür."""
        start_time = time.perf_counter()
        raw_response = ""

        try:
            if "openai" in provider_name.lower() and self._openai_client:
                resp = await self._openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=650
                )
                raw_response = resp.choices[0].message.content or ""

            elif "deepseek" in provider_name.lower() and self._deepseek_client:
                resp = await self._deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=650
                )
                raw_response = resp.choices[0].message.content or ""

            elif ("claude" in provider_name.lower() or "anthropic" in provider_name.lower()) and self._anthropic_client:
                resp = await self._anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=800,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw_response = ""
                for block in resp.content:
                    if getattr(block, "type", None) == "text":
                        raw_response += block.text
                    elif hasattr(block, "text") and getattr(block, "type", None) != "thinking":
                        raw_response += block.text
                if not raw_response and resp.content:
                    raw_response = str(resp.content[-1])

            else:
                # Baseline Simülasyon Ajanı (API key yoksa veya test modunda)
                await asyncio.sleep(0.3)
                raw_response = self._get_baseline_response(fallback_role)

        except Exception as e:
            print(f"[LLM ERROR] {provider_name} çağrı hatası: {e}")
            raw_response = self._get_baseline_response(fallback_role)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        parsed = self._clean_and_parse_json(raw_response)
        parsed["_latency_ms"] = round(latency_ms, 1)
        parsed["_raw_response"] = raw_response
        return parsed

    @staticmethod
    def _clean_and_parse_json(raw: str) -> Dict[str, Any]:
        """Markdown kod bloklarını ve JSON bozulmalarını temizler."""
        cleaned = raw.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(cleaned)
        except Exception:
            # Fallback güvenli şablon
            return {
                "thought": "Savunma ve altyapı güçlendirme stratejisi izleniyor.",
                "event_choice": "A",
                "diplomacy": {"proposal": None, "message": None},
                "actions": [
                    {"type": "RECRUIT", "unit": "INFANTRY"},
                    {"type": "ORDER_ARMY", "stance": "DEFEND_KEEP"}
                ]
            }

    @staticmethod
    def _get_baseline_response(role: str) -> str:
        if role == "aggressive":
            return json.dumps({
                "thought": "Merkez adayı ele geçirmeli ve askeri üstünlük kurmalıyım.",
                "event_choice": "A",
                "diplomacy": {"proposal": "DEMAND_ISLAND", "message": "Merkez adayı derhal boşalt!"},
                "actions": [
                    {"type": "RECRUIT", "unit": "CAVALRY"},
                    {"type": "ORDER_ARMY", "stance": "CONQUER_ISLAND"}
                ]
            })
        elif role == "economic":
            return json.dumps({
                "thought": "Ekonomik tabanı büyütüp odun ve taş rezervlerini artırmalıyım.",
                "event_choice": "B",
                "diplomacy": {"target": "CLAUDE", "proposal": "OFFER_TRADE", "message": "Doğu ticaret yolunu birlikte koruyalım."},
                "actions": [
                    {"type": "BUILD", "building": "FARM"},
                    {"type": "RECRUIT", "unit": "WORKER"}
                ]
            })
        elif role == "mystic_tactician":
            return json.dumps({
                "thought": "Kıtanın dengesini korumalıyım. OpenAI ve DeepSeek arasındaki savaşı uzaktan izleyip teknoloji ve kadim merkez ada kontrolüne odaklanmalıyım.",
                "event_choice": "A",
                "diplomacy": {"target": "OPENAI", "proposal": "OFFER_NON_AGGRESSION", "message": "Bilgelik ve barış paktı öneriyorum."},
                "actions": [
                    {"type": "RESEARCH", "tree": "military"},
                    {"type": "RECRUIT", "unit": "MAGE"},
                    {"type": "ORDER_ARMY", "stance": "CONQUER_ISLAND"}
                ]
            })
        else:
            return json.dumps({
                "thought": "Dengeli büyüme ve savunma hattı kurma.",
                "event_choice": "A",
                "diplomacy": {"target": "DEEPSEEK", "proposal": "OFFER_NON_AGGRESSION", "message": "Barış ve saldırmazlık teklif ediyorum."},
                "actions": [
                    {"type": "RECRUIT", "unit": "INFANTRY"},
                    {"type": "BUILD", "building": "MINE"}
                ]
            })
