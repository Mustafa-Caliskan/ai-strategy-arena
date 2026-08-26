"""
google_provider.py — Google Gemini provider (Stub - Faz 3+)
"""
from __future__ import annotations
from ai.base_provider import AIProvider


class GoogleProvider(AIProvider):
    def __init__(self, agent_id: str, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.3):
        super().__init__(agent_id, model, temperature)
        self._api_key = api_key

    async def decide_async(self, system_prompt: str, user_prompt: str) -> str:
        import google.generativeai as genai
        self._call_count += 1
        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self.model_name)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = await model.generate_content_async(full_prompt)
        return response.text
