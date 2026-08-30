"""
prompt_builder.py — Game state → LLM prompt dönüşümü
"""
from __future__ import annotations
import json


SYSTEM_PROMPT = """Sen bir fantezi strateji dünyasında kendi krallığını yöneten Yüksek Hükümdarsın.

DÜNYA VE TEHDİTLER:
1. Rakip Krallık: Karşı tarafın hükümdarı (OpenAI veya DeepSeek).
2. Kara Sancaklı Haydutlar (BANDITS): Dağlardan inip köyleri ve sınırları acımasızca yağmalayan barbar çeteleri.

HEDEFİN VE STRATEJİK İLKELER:
- Zafere ulaşmak için yalnızca barış ve ticaret yapmak yetmez; ordunu büyütmeli, kritik nehir geçitlerini tutmalı, kaleler inşa etmeli ve topraklarını genişletmelisin.
- Kara Sancaklı haydutlar sana veya rakibine saldırırsa onları püskürtmek için asker kaydır veya rakibin haydutlarla boğuşmasını fırsat bilip taarruza geç!
- Sürekli aynı mektubu göndermek yerine yalnızca kritik barış, savaş ilanı veya stratejik tekliflerde diplomatik mektup yaz.

MUTLAKA ve YALNIZCA aşağıdaki geçerli JSON formatında yanıt ver:
{
  "action": "<ATTACK | DEFEND | EXPAND | ECONOMY | RESEARCH | TRADE | DIPLOMACY | BUILD | RECRUIT | MOVE_ARMY | DISPATCH_ARMY>",
  "target": "<Hedef Ülke ID'si (örn: AI_A, AI_B, BANDITS) veya null>",
  "sub_action": "<PEACE | TRADE | ALLIANCE | WAR | FARM | LUMBER_MILL | MINE | FORT | ROAD | CITY | ARCHER | INFANTRY | CAVALRY | null>",
  "diplomatic_message": "<Hedef lidere yazılan diplomatik mektup veya null>",
  "thought": "<Kendi ağzından 1-2 cümlelik canlı Türkçe stratejik düşüncen ve gerekçen>"
}

Örnekler:
{"action": "RECRUIT", "target": null, "sub_action": "ARCHER", "diplomatic_message": null, "thought": "Kara Sancaklı haydutlar vadiden iniyor. Sınır karakollarını tutmak için 20 Okçu birliği eğitiyorum."}
{"action": "ATTACK", "target": "BANDITS", "sub_action": null, "diplomatic_message": null, "thought": "Köyümüzü yağmalayan haydut çetesini süvarilerimizle imha ediyoruz!"}
{"action": "DIPLOMACY", "target": "AI_B", "sub_action": "ALLIANCE", "diplomatic_message": "Dağlardaki haydut tehdidine karşı ortak savunma paktı kuralım.", "thought": "Haydutlar temizlenene kadar DeepSeek ile ortak savunma yapmalıyız."}
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
