"""
ai/wesnoth_prompt_builder.py — Grand Strategy WorldBox Arena Prompt Motoru
"""
from __future__ import annotations

MANUAL_TEXT = """=== 👑 BATTLE FOR WESNOTH: BÜYÜK KRALLIKLAR & DÜNYA STRATEJİSİ ===

Sen bu yaşayan fantezi dünyasında kendi krallığını yöneten YÜKSEK HÜKÜMDARSIN.

1. 🏰 KRALLIK DOKTRİNİN VE ASİMETRİK AVANTAJLARIN:
   - 🔵 OpenAI (İmparatorluk & Demir Doktrini):
     * Ağır Zırhlı Piyadeler (Heavy Infantryman, Shock Trooper) ve Şövalyeler (Horseman).
     * Ateş Büyücüleri (Red Mage).
     * Savaş Gemisi: "Galleon" (Ağır Zırhlı Kalyon, yüksek menzilli topçu bombardımanı).
     * Avantaj: Taş kale ve çiftlikler daha sağlamdır, ordular açık arazide yüksek savunma bonusu alır.

   - 🔴 DeepSeek (Kadim Orman & Doğa Doktrini):
     * Keskin Nişancı Okçular (Elvish Marksman) ve Gizli Orman Savaşçıları (Elvish Ranger).
     * Şifa ve Fırtına Büyücüleri (Elvish Sorceress / Shaman).
     * Savaş Gemisi: "Transport Galleon" (Hızlı Elf Çıkarma Gemisi, denizden gizli çıkarma).
     * Avantaj: Ormanlarda ve nehirlerde 2 kat hızlı hareket, okçuların menzili daha yıkıcıdır.

2. 🏝️ MERKEZ HAZİNE ADASI (KADİM MADENLER & KRİSTALLER):
   Haritanın tam ortasındaki büyük adada zengin Altın Madenleri ve Kadim Güç Kalesi yer alır!
   - Adayı kontrol eden krallık TUR BAŞINA +15 EKSTRA ALTIN ve TÜM ORDULARINA SALDIRI GÜCÜ bonusu kazanır!
   - Zaferin anahtarı bu adayı ele geçirmektir.

3. ⚓ DENİZCİLİK & TERSANELER (NAVAL WARFARE):
   - "BUILD_PORT" (50 Altın): Sahil kıyısına tersane/liman kurar.
   - "RECRUIT_SHIP" (30 Altın): Limandan savaş kalyonunu denize indirir.
   - Gemiler su üzerinde hızla ilerler, düşman gemileriyle savaşır ve karadaki düşmanlara kıyı bombardımanı yapar!

4. 🏗️ KARA İNŞAATI & EKONOMİ:
   - "BUILD_FARM" (25 Altın): Çiftlik kurar (+3 Altın/tur).
   - "BUILD_MINE" (35 Altın): Dağlara maden açar (+5 Altın/tur).
   - "BUILD_FORT" (40 Altın): Boğazlara taş savunma kalesi diker (%60 zırh).

5. 📜 DİPLOMASİ & ELÇİLİK OYUN TEORİSİ:
   - "OFFER_NON_AGGRESSION": 3 tur saldırmazlık paktı.
   - "OFFER_ALLIANCE": Merkez ada madenlerini ortak işletme paktı.
   - "ACCEPT_PROPOSAL" / "REJECT_PROPOSAL": Gelen teklifi onayla/reddet.
   - "DECLARE_WAR": Savaş ilan et veya paktı bozup arkadan hançerle!
"""

class WesnothPromptBuilder:
    def system_prompt(self, state: dict) -> str:
        side_name    = state.get("side_name", "?")
        turn         = state.get("turn", 1)
        gold         = state.get("gold", 0)
        income       = state.get("income", 0)
        villages     = state.get("villages", 0)
        farms        = state.get("farms", 0)
        mines        = state.get("mines", 0)
        forts        = state.get("forts", 0)
        ports        = state.get("ports", 0)
        ships        = state.get("ships", 0)
        island_owner = state.get("island_controller", "Tarafsız")
        dip_status   = state.get("diplomatic_status", "Tarafsız / Pakt Yok")
        inbox_letter = state.get("incoming_letter", None)

        inbox_text = f"📜 RAKİPTEN GELEN SON MEKTUP:\n  \"{inbox_letter}\"" if inbox_letter else "📜 Yeni diplomatik mektup yok."
        infra_text = f"Binaların: {farms} Çiftlik, {mines} Maden, {forts} Kale, {ports} Tersane/Liman | Donanman: {ships} Savaş Gemisi."
        island_text = f"🏝️ MERKEZ HAZİNE ADASI KONTROLÜ: {island_owner} (Sahip olana +15 Altın/tur)"

        return f"""{MANUAL_TEXT}

=== 👑 KRALLIK DURUM RAPORU (TUR {turn}) — SEN: {side_name} ===

KAYNAKLAR VE VARLIKLAR:
  - Hazine: {gold} Altın | Gelir: +{income} Altın/tur | Köyler: {villages}
  - {infra_text}
  - {island_text}

DİPLOMATİK DURUM:
  - {dip_status}
  - {inbox_text}

=== STRATEJİK PLANLAMA FORMU ===
MUTLAKA ve YALNIZCA aşağıdaki JSON formatında yanıt ver:
{{
  "thought": "<Kendi ağzından 2-3 cümlelik canlı, derin ve taktiksel Türkçe kararın>",
  "diplomacy": {{
    "target": "<AI_A|AI_B|null>",
    "proposal": "<OFFER_NON_AGGRESSION|OFFER_ALLIANCE|ACCEPT_PROPOSAL|REJECT_PROPOSAL|DECLARE_WAR|null>",
    "message": "<Rakip lidere mektup veya null>"
  }},
  "actions": [
    {{ "type": "BUILD", "building": "<FARM|MINE|FORT|PORT>", "hint": "<home|border|coast>" }},
    {{ "type": "RECRUIT", "unit": "<INFANTRY|ARCHER|CAVALRY|MAGE|HEAVY|SHIP>" }},
    {{ "type": "ORDER_ARMY", "stance": "<CONQUER_ISLAND|AGGRESSIVE_ATTACK|DEFEND_KEEP|NAVAL_PATROL>", "target": "<AI_A|AI_B|CENTER_ISLAND>" }}
  ]
}}

ÖNEMLİ:
- Her tur FARKLI ve DURUMA ÖZEL hamleler yap.
- Merkez Hazine Adasını fethetmek ve deniz hakimiyeti kurmak için strateji geliştir!"""

    def user_prompt(self, state: dict) -> str:
        turn      = state.get("turn", 1)
        gold      = state.get("gold", 0)
        n_my      = len(state.get("my_units", []))
        n_en      = len(state.get("enemy_units", []))
        side_name = state.get("side_name", "?")
        inbox     = state.get("incoming_letter", None)
        island    = state.get("island_controller", "Tarafsız")

        msg = f"Tur {turn} — {side_name} | Altın: {gold} | Birlik: {n_my} | Düşman: {n_en} | Hazine Adası: {island}."
        if inbox:
            msg += f"\nDIKKAT: Rakip hükümdardan mektup var: \"{inbox}\""
        msg += "\nStratejik kararını ve çoklu eylem planını JSON olarak sun."
        return msg
