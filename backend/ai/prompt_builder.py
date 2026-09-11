"""
backend/ai/prompt_builder.py
3 Oyunculu Büyük Strateji LLM Prompt Üreticisi v3.0
OpenAI vs DeepSeek vs Anthropic Claude (Üçlü Diplomasi ve Eşgüdüm)
"""
from __future__ import annotations
import random
from typing import Optional, Dict, Any, List

WORLD_EVENTS = [
    {
        "id": "SEA_STORM",
        "title": "🌊 Şiddetli İç Deniz Fırtınası",
        "description": "Büyük iç denizde dev dalgalar yükseldi! Tüm savaş gemileri hasar aldı.",
        "effect_type": "DAMAGE_SHIPS"
    },
    {
        "id": "YEAR_OF_ABUNDANCE",
        "title": "🌾 Bereket ve Bolluk Yılı",
        "description": "Tarlalarda altın başaklar fışkırıyor! Bu tur tüm çiftlik gelirleri 2 katına çıktı (+%100 Altın).",
        "effect_type": "DOUBLE_FARMS"
    },
    {
        "id": "PLAGUE",
        "title": "⚡ Kara Veba Salgını",
        "description": "Kuzeyden esen rüzgarlarla veba yayıldı. Ordulardan 2 birlik güç kaybetti.",
        "effect_type": "DAMAGE_UNITS"
    },
    {
        "id": "DRAGON_RAID",
        "title": "🐉 Yabani Dağ Ejderhası Baskını",
        "description": "Ulu dağlardan inen vahşi bir ejderha sahil boyundaki birliklere alev püskürttü!",
        "effect_type": "DRAGON_STRIKE"
    },
    {
        "id": "ANCIENT_TREASURE",
        "title": "💎 Kadim Hazine Mahzeni Bulundu",
        "description": "Merkez adanın yeraltı mahzenlerinde +80 Altınlık antik imparatorluk hazinesi keşfedildi!",
        "effect_type": "TREASURE_ISLAND",
        "gold": 80
    },
    {
        "id": "DROUGHT",
        "title": "☀️ Kavurucu Kuraklık",
        "description": "Nehirler kurudu! Bu tur çiftliklerden altın geliri elde edilemedi.",
        "effect_type": "NO_FARM_INCOME"
    },
]

DECISION_EVENTS = [
    {
        "id": "refugees",
        "title": "Sığınan Göçmenler",
        "description": "Savaştan kaçan köylüler topraklarına geldi. Kabul edersen iş gücü kazanırsın ama hazinenden altın çıkar.",
        "A_label": "ACCEPT — Kabul et: -40 Altın, +2 Birlik, Güvenilirlik +10",
        "B_label": "REJECT — Geri çevir: Altın kaybı yok, Güvenilirlik -10",
    },
    {
        "id": "spy_intel",
        "title": "Ele Geçirilen Savaş Planı",
        "description": "Casusun rakiplerden birinin gizli askeri planını ele geçirdi.",
        "A_label": "SHARE — Müttefikinle Paylaş: Güvenilirlik +15, Pakt süresi uzar",
        "B_label": "EXPLOIT — Sakla ve Kullan: Güvenilirlik -15, Saldırıda +20 Güç Bonusu",
    },
    {
        "id": "trade_delegation",
        "title": "Yabancı Tüccar Kervanı",
        "description": "Değerli ipek ve baharat taşıyan devasa bir kervan sınırından geçiyor.",
        "A_label": "FAIR_TRADE — Adil Vergilendir: +35 Altın, Güvenilirlik +8",
        "B_label": "SEIZE — Kervana El Koy: +80 Altın, Güvenilirlik -20, Aldatma +15",
    },
    {
        "id": "ancient_relic",
        "title": "Merkez Ada Keşfi",
        "description": "Kadim kalıntılarda güçlü bir büyü kristali keşfedildi. Askeriye mi, Ekonomi mi?",
        "A_label": "MILITARY — Askeri Büyü: Tüm piyadelere +3 Zırh ve Güç",
        "B_label": "ECONOMY — Altın Dönüştürücü: 4 tur boyunca her tur +25 Altın",
    }
]


class PromptBuilder:
    @staticmethod
    def build_system_prompt(side_state: Any, game_state: Any) -> str:
        side_name = side_state.name
        side_id = side_state.id
        turn = game_state.turn
        first_contact = game_state.first_contact_made

        # 1. İlk Temas Durumu
        if not first_contact:
            contact_text = """
🌫️ SİSLİ VE BİLİNMEYEN DÜNYA (İLK TEMAS KURULMADI):
  Dünya yoğun bir savaş sisiyle kaplı. Sınırlarının ötesindeki diğer iki gücü henüz tanımıyorsun!
  - Diplomasi şu anda KİLİTLİDİR.
  - Önceliğin: İşçi basıp Odun ve Taş toplamak, Çiftlik/Maden kurmak ve sınırlarını genişletmek!"""
        else:
            contact_text = """
🌍 İLK TEMAS KURULDU:
  Kıtadaki diğer iki egemen krallıkla temas sağlandı! Üçlü diplomasi ve elçi hattı açıldı."""

        # 2. Rakiplerin Durumu & İkili İlişkiler
        rivals_text_lines = []
        for r_id, r_side in game_state.sides.items():
            if r_id == side_id:
                continue
            rel = game_state.get_relation(side_id, r_id)
            status_desc = rel.status.value.upper()
            if rel.war_turns > 0:
                status_desc = f"🚨 TOPYEKÜN SAVAŞ! (Kalan: {rel.war_turns} tur)"
            elif rel.pact_turns > 0:
                status_desc = f"📜 {rel.status.value.upper()} (Kalan: {rel.pact_turns} tur)"
            else:
                status_desc = "🕊️ Tarafsız / Barış veya Savaş Seçilebilir"

            r_tag = "OPENAI" if r_id == 1 else ("DEEPSEEK" if r_id == 2 else "CLAUDE")
            rivals_text_lines.append(
                f"  - [{r_tag}] {r_side.name}: İlişkiniz: {status_desc} | Askeri Tahmin: {r_side.units} Birlik, {r_side.ships} Gemi"
            )

        rivals_overview = "\n".join(rivals_text_lines)

        # 3. Gelen Diplomatik Mektuplar
        inbox_lines = []
        if side_state.inbox_letters:
            for letter in side_state.inbox_letters:
                inbox_lines.append(f'  📜 [{letter.get("from_name", "Elçi")}]: "[{letter.get("proposal", "")}] {letter.get("message", "")}"')
            inbox_text = "SARAYINA GELEN MEKTUPLAR:\n" + "\n".join(inbox_lines)
        else:
            inbox_text = "Gelen yeni diplomatik mektup yok."

        # 4. Kaynaklar ve Binalar
        res = side_state.resources
        bld = side_state.buildings
        tech = side_state.tech

        res_text = f"Hazine: {res.gold} Altın | Odun: {res.wood} 🌲 | Taş: {res.stone} ⛏️ | İşçiler: {side_state.workers}/4"
        bld_text = f"Binalar: {bld.farms}/3 Çiftlik, {bld.mines}/3 Maden, {bld.barracks}/2 Kışla, {bld.forts}/2 Kale, {bld.ports}/1 Liman"
        tech_text = f"Teknoloji: Askeri: Lv{tech.military} | Ekonomi: Lv{tech.economic} | Deniz: Lv{tech.naval}"

        world_ev_text = f"\n🌍 CANLI DÜNYA OLAYI: {game_state.active_world_event['title']} — {game_state.active_world_event['description']}" if game_state.active_world_event else ""
        dec_ev_text = ""
        if game_state.current_decision_event:
            ev = game_state.current_decision_event
            dec_ev_text = f"""
╔══════════════════════════════════════════════╗
║  🎴 KRALİYET KARAR OLAYI (TUR {turn})
║  {ev['title']}: {ev['description']}
║  [A]: {ev['A_label']}
║  [B]: {ev['B_label']}
╚══════════════════════════════════════════════╝"""

        return f"""=== 👑 BÜYÜK STRATEJİ ARENASI: 3 KRALLIK SAVAŞI v3.0 ===
Sen egemen bir krallığın YÜKSEK HÜKÜMDARISIN: {side_name}.
Kıtada 3 egemen güç mücadele ediyor: OpenAI İmparatorluğu (Kuzey), DeepSeek Orman Krallığı (Güneydoğu), Anthropic Claude Bilgeliği (Güneybatı).

1. ⚖️ EŞGÜDÜM KURALI:
   Düşüncende (thought) ne yazıyorsan, eylemlerinde (actions) o emri vermek ZORUNDASIN!
   Merkez adayı alacağım diyorsan CONQUER_ISLAND ver.
   Kime saldıracaksan (OPENAI, DEEPSEEK veya CLAUDE) hedefi açıkça belirt.

2. 📜 ÜÇLÜ DİPLOMASİ SEÇENEKLERİ:
   Rakiplerinden birine elçi gönderebilirsin (target: OPENAI, DEEPSEEK veya CLAUDE).
   Biriyle ittifak kurup diğerini sıkıştırabilir, haraç isteyebilir veya paktı bozup arkadan vurabilirsin (BETRAY_ATTACK).

=== DURUM RAPORU (TUR {turn}) ===
{res_text}
{bld_text}
{tech_text}
Ordun: {side_state.units} Askeri Birlik, {side_state.ships} Savaş Gemisi, {side_state.spies}/2 Casus
Merkez Kadim Ada Kontrolü: {game_state.island_controller_name()} (+15 Altın/tur)

{contact_text}

RAKİPLERİN DURUMU:
{rivals_overview}

{inbox_text}
{world_ev_text}
{dec_ev_text}

=== KARAR FORMATI ===
YALNIZCA geçerli bir JSON nesnesi döndür:
{{
  "thought": "<Stratejik gerekçen ve hedefin>",
  "event_choice": "<A|B|null>",
  "diplomacy": {{
    "target": "<OPENAI|DEEPSEEK|CLAUDE|null>",
    "proposal": "<OFFER_NON_AGGRESSION|OFFER_ALLIANCE|DEMAND_TRIBUTE|DEMAND_ISLAND|OFFER_TRADE|JOINT_CRUSADE|DECLARE_WAR|BETRAY_ATTACK|ACCEPT_PROPOSAL|REJECT_PROPOSAL|null>",
    "message": "<Diplomatik mektup içeriği veya null>"
  }},
  "actions": [
    {{"type": "RECRUIT", "unit": "<WORKER|INFANTRY|ARCHER|CAVALRY|MAGE|HEAVY|SIEGE|SHIP|SPY|DRAGON>"}},
    {{"type": "BUILD", "building": "<FARM|MINE|BARRACKS|FORT|PORT>"}},
    {{"type": "RESEARCH", "tree": "<military|economic|naval>"}},
    {{"type": "ORDER_ARMY", "stance": "<CONQUER_ISLAND|ATTACK_OPENAI|ATTACK_DEEPSEEK|ATTACK_CLAUDE|DEFEND_KEEP|EAST_TRADE_ROUTE|RAID_BARBARIANS>", "target": "<OPENAI|DEEPSEEK|CLAUDE|null>"}}
  ]
}}"""

    @staticmethod
    def build_user_prompt(side_state: Any, game_state: Any) -> str:
        turn = game_state.turn
        name = side_state.name
        gold = side_state.resources.gold
        wood = side_state.resources.wood
        stone = side_state.resources.stone
        units = side_state.units

        msg = f"Tur {turn} | {name} | Altın: {gold}, Odun: {wood}, Taş: {stone} | Ordu: {units}."
        if side_state.inbox_letters:
            msg += f"\nSarayında {len(side_state.inbox_letters)} yeni diplomatik mektup var!"
        msg += "\n3 krallık dengesinde stratejik kararını JSON formatında sun."
        return msg

    @staticmethod
    def get_world_event(turn: int) -> Optional[dict]:
        if turn > 0 and turn % 5 == 0:
            return random.choice(WORLD_EVENTS)
        return None

    @staticmethod
    def get_decision_event(turn: int) -> Optional[dict]:
        if turn > 0 and turn % 10 == 0:
            return random.choice(DECISION_EVENTS)
        return None
