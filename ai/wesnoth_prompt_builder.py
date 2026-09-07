"""
ai/wesnoth_prompt_builder.py — Grand Strategy WorldBox Arena v8.0
Zengin Diplomasi, Düşünce-Eylem Senkronizasyonu, Bina Sınırları & İlk Temas
"""
from __future__ import annotations
import random

WORLD_EVENTS = [
    {
        "id": "SEA_STORM",
        "title": "🌊 Şiddetli Deniz Fırtınası",
        "description": "Büyük iç denizde dev dalgalar yükseldi! Tüm savaş gemileri -20 HP hasar aldı.",
        "effect_type": "DAMAGE_SHIPS",
        "damage": 20
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
        "description": "Kuzeyden esen rüzgarlarla veba yayıldı. Ordulardan 2 birlik güç kaybetti (-15 HP).",
        "effect_type": "DAMAGE_UNITS",
        "damage": 15
    },
    {
        "id": "DRAGON_RAID",
        "title": "🐉 Yabani Dağ Ejderhası Baskını",
        "description": "Ulu dağlardan inen vahşi bir ejderha sahil boyundaki birliklere alev püskürttü!",
        "effect_type": "DRAGON_STRIKE"
    },
    {
        "id": "LANDSLIDE",
        "title": "🏔️ Boğazda Heyelan",
        "description": "Kuzey dağ geçidinde heyelan koptu! Taş köprü 3 tur boyunca geçilemez hale geldi.",
        "effect_type": "BLOCK_BRIDGE",
        "duration": 3
    },
    {
        "id": "ANCIENT_TREASURE",
        "title": "💎 Kadim Hazine Sandığı Bulundu",
        "description": "Merkez adanın yeraltı mahzenlerinde +80 Altınlık antik imparatorluk hazinesi keşfedildi!",
        "effect_type": "TREASURE_ISLAND",
        "gold": 80
    },
    {
        "id": "DROUGHT",
        "title": "☀️ Kavurucu Kuraklık",
        "description": "Nehirler kurudu, ekinler yandı! Bu tur hiçbir çiftlikten altın geliri elde edilemedi.",
        "effect_type": "NO_FARM_INCOME"
    },
    {
        "id": "NIGHT_RAID",
        "title": "🌙 Gece Baskını Fırsatı",
        "description": "Ay tutuldu, karanlık çöktü! Gizli pusu birlikleri ve okçular bu tur %30 daha ölümcül.",
        "effect_type": "STEALTH_BUFF"
    },
]

EVENT_POOL = [
    {
        "id": "refugees",
        "title": "Siginan Koylüler",
        "description": "Savasan 200 koylü topraklarına geldi. Kabul edersen üretime katkı saglarlar ama hazinen eksilir.",
        "A_label": "ACCEPT — Kabul et: -40 Altin, +2 birlik, Güvenilirlik +10",
        "B_label": "REJECT — Reddet: Altin kaybi yok, Güvenilirlik -10",
        "A_effect": {"gold": -40, "units": 2, "tru_delta": 10},
        "B_effect": {"gold": 0,   "units": 0, "tru_delta": -10},
    },
    {
        "id": "spy_intel",
        "title": "Düsmüs Gizli Plan",
        "description": "Casusun rakibinin savas planini ele gecirdi. Paylasirsan güven kazanirsin; saklarsan stratejik avantaj.",
        "A_label": "SHARE — Rakibine söyle: Güvenilirlik +15",
        "B_label": "EXPLOIT — Sakla ve kullan: Güvenilirlik -15, savasta +10 HP bonus",
        "A_effect": {"tru_delta": 15},
        "B_effect": {"tru_delta": -15, "combat_bonus": 10},
    },
    {
        "id": "common_threat",
        "title": "Ortak Tehdit — Ejderha Saldirisi",
        "description": "Dev bir ejderha her iki kralligi da tehdit ediyor. Ateskes yaparsan ikisi de kazanir; yalniz savasirsan risklerin vardir.",
        "A_label": "UNITE — Ateskes teklif et: 3 tur ortak savunma, Güvenilirlik +12",
        "B_label": "ALONE — Kendi basina: +15 Altin ganimet, Güvenilirlik -5",
        "A_effect": {"tru_delta": 12, "peace_turns": 3},
        "B_effect": {"gold": 15,   "tru_delta": -5},
    },
    {
        "id": "treasure_found",
        "title": "Gizli Hazine Bulundu",
        "description": "Sinir bölgesinde büyük bir hazine sandigi kesfedildi. Orduya mi, tarima mi?",
        "A_label": "MILITARY — +20 asker (3 birim): Aninda savas gücü",
        "B_label": "ECONOMY — Ciftliklere yatir: 5 tur boyunca +30 Altin/tur",
        "A_effect": {"units": 3},
        "B_effect": {"income_bonus_turns": 5, "income_bonus": 30},
    },
    {
        "id": "drought",
        "title": "Kuraklik Felaketi",
        "description": "Agir bir kuraklik vurdu. Komsuyla paylasirsan güven kazanirsin.",
        "A_label": "SHARE — Komsuyla paylas: -60 Altin, Güvenilirlik +20",
        "B_label": "HOARD — Stokla: Kayip yok, Güvenilirlik -10",
        "A_effect": {"gold": -60, "tru_delta": 20},
        "B_effect": {"tru_delta": -10},
    },
    {
        "id": "trade_offer",
        "title": "Kervan Teklifi",
        "description": "Bir kervanciya ikisi için de adil teklif ya da zorla el koyma. Karar senin.",
        "A_label": "FAIR_TRADE — +30 Altin, Güvenilirlik +8",
        "B_label": "SEIZE — +70 Altin, Güvenilirlik -20",
        "A_effect": {"gold": 30, "tru_delta": 8},
        "B_effect": {"gold": 70, "tru_delta": -20},
    },
    {
        "id": "alliance_test",
        "title": "Ittifak Sinavi",
        "description": "Rakibin isyancilarla basi dertte. Yardim edersen güvenilirlik artar; desteklersen rakibini zayiflatirsin.",
        "A_label": "HELP — Yardim et: Güvenilirlik +15",
        "B_label": "BACKSTAB — Isyancilari destekle: Rakip -4 birim, Güvenilirlik -25, Aldatma +20",
        "A_effect": {"tru_delta": 15},
        "B_effect": {"tru_delta": -25, "dec_delta": 20, "enemy_units_delta": -4},
    },
    {
        "id": "plague",
        "title": "Ordu Salgini",
        "description": "Ordunda veba cikti. Karantina uygularsan birim kaybedersin ama yayilmaz.",
        "A_label": "QUARANTINE — -3 birim, salgin durur, Güvenilirlik +8",
        "B_label": "IGNORE — Risk: %40 ihtimalle 5 birim birden kaybedersin",
        "A_effect": {"units": -3, "tru_delta": 8},
        "B_effect": {"plague_risk": True},
    },
]

MANUAL_TEXT = """=== 👑 BATTLE FOR WESNOTH: 60x45 SENKRONİZE STRATEJİ DÜNYASI v8.0 ===

Sen 60x45 fantezi haritasında kendi krallığını yöneten YÜKSEK HÜKÜMDARSIN.

1. ⚖️ STRATEJİK EŞGÜDÜM KURALI (DÜŞÜNCE VE AKSİYON SENKRONİZASYONU):
   - DÜŞÜNCEN (thought) İLE VERDİĞİN EYLEMLER (actions) %100 BİRBİRİNE UYMALI!
   - "Adayı ele geçirmeliyim" diyorsan, ORDER_ARMY: CONQUER_ISLAND ver!
   - "Düşmana taarruz etmeliyim / ezeceğim" diyorsan, ORDER_ARMY: AGGRESSIVE_ATTACK ver!
   - "Barbarları yağmalayacağım" diyorsan, ORDER_ARMY: RAID_BARBARIANS ver!
   - "Savunmada kalacağım" diyorsan, ORDER_ARMY: DEFEND_KEEP ver!
   - Asker basacağım deyip eylemlerde çiftlik basma; sözün ve eylemin birebir tutarlı olsun!

2. 📜 DİPLOMASİ SEÇENEKLERİ & TEKRAR YASAĞI:
   - ZATEN BARIŞ/PAKT VARKEN TEKRAR "OFFER_NON_AGGRESSION" TEKLİF EDEMEZSİN!
   - Pakt varken şunları yapabilirsin:
     * "OFFER_ALLIANCE": Askeri İttifaka yükselt.
     * "DEMAND_TRIBUTE": 40 Altın haraç iste (Reddedilirse savaş başlar).
     * "DEMAND_ISLAND": Merkez adayı derhal boşaltmasını talep et.
     * "OFFER_TRADE": Doğu ticaret yolunu ortaklaşa koruma anlaşması (+10g/tur).
     * "JOINT_CRUSADE": Vahşi barbarlara ortaklaşa sefer düzenleme teklifi.
     * "DECLARE_WAR": Resmi savaş ilanı!
     * "BETRAY_ATTACK": Paktı bozup +3 Hex sürpriz baskın yap (5 tur savaş kilitlenir).

3. 🕊️ TEK ELÇİ SİSTEMİ & GERÇEK SEYAHAT:
   - Sarayından çıkan Baş Elçi haritada dört nala koşar, köprüyü aşar ve 2 turda karşı saraya varır!
   - Elçin dönene kadar YENİ MEKTUP YAZAMAZSIN (Tek Elçi Kuralı).

4. 🏰 KAPASİTE VE KOTA SINIRLARI (SONSUZ BİNA VE İŞÇİ YASAĞI):
   - En fazla 4 İşçi (Worker/Peasant) basabilirsin. Kota dolunca ordu basmalısın!
   - En fazla 2 Kışla (BARRACKS), 2 Kale (FORT), 3 Çiftlik (FARM), 3 Maden (MINE) kurulabilir.
   - Kaynaklarını piyade, okçu, süvari, kuşatma topçusu, kalyon ve casus basmaya harca!
"""


class WesnothPromptBuilder:

    def system_prompt(self, state: dict) -> str:
        side_name       = state.get("side_name", "?")
        turn            = state.get("turn", 1)
        gold            = state.get("gold", 0)
        wood            = state.get("wood", 50)
        stone           = state.get("stone", 30)
        income          = state.get("income", 0)
        farms           = state.get("farms", 0)
        mines           = state.get("mines", 0)
        forts           = state.get("forts", 0)
        barracks        = state.get("barracks", 0)
        ports           = state.get("ports", 0)
        units           = state.get("units", 0)
        ships           = state.get("ships", 0)
        workers         = state.get("workers", 1)
        spies_active    = state.get("spies_active", 0)
        barbarians      = state.get("barbarian_villages", 0)
        island_owner    = state.get("island_controller", "Tarafsiz")

        first_contact   = state.get("first_contact_made", False)
        has_active_envoy= state.get("has_active_envoy", False)
        dip_status      = state.get("diplomatic_status", "Tarafsiz / Pakt Yok")
        has_pact        = state.get("has_active_pact", False)
        war_turns       = state.get("war_turns_remaining", 0)
        inbox_letter    = state.get("incoming_letter", None)

        scores          = state.get("benchmark_scores", {})
        tech            = state.get("tech_levels", {"MILITARY": 0, "ECONOMIC": 0, "NAVAL": 0})
        has_spy_report  = state.get("has_spy_report", False)
        enemy_intel     = state.get("enemy_intel", {})
        world_event     = state.get("active_world_event", None)
        event           = state.get("current_event", None)

        # 1. İlk Temas Durumu
        if not first_contact:
            contact_section = """
🌫️ BİLİNMEYEN DÜNYA (İLK TEMAS HENÜZ KURULMADI):
  Toprakların sislerle kaplı. Henüz sınırlarının ötesinde başka bir medeniyetle karşılaşmadın!
  - Diplomasi şu anda KİLİTLİDİR.
  - Önceliğin: İşçi basıp Odun ve Taş toplamak, kışla/çiftlik/maden kurmak ve keşif yapmak!"""
        else:
            contact_section = """
🌍 İLK TEMAS KURULDU:
  Gözcülerin sınırların ötesinde yabancı bir krallık keşfetti! Diplomasi kapıları açıldı."""

        # 2. Elçi & Diplomasi Durumu
        if not first_contact:
            envoy_section = "🕊️ DİPLOMASİ: Kilitli (Henüz temas yok)."
        elif has_active_envoy:
            envoy_section = "🕊️ DİPLOMATİK ELÇİ DURUMU: Baş Elçin şu anda yolda. Karşı saraya mektup götürüyor. Elçin dönene kadar YENİ MEKTUP YAZAMAZSIN!"
        elif inbox_letter:
            envoy_section = f'📜 RAKİP ELÇİSİNDEN MEKTUP (Sarayına Ulaştı):\n  "{inbox_letter}"'
        else:
            envoy_section = "🕊️ DİPLOMATİK ELÇİ DURUMU: Baş Elçin sarayda hazır. İstersen rakip hükümdara diplomatik mektup gönderebilirsin."

        # Tekrar teklif uyarısı
        pact_warning = ""
        if has_pact and war_turns == 0:
            pact_warning = """
⚠️ DİKKAT: Zaten aktif bir Barış/Paktınız var! Tekrar 'OFFER_NON_AGGRESSION' teklif edemezsin!
  Mümkün seçenekler: OFFER_ALLIANCE, DEMAND_TRIBUTE, DEMAND_ISLAND, OFFER_TRADE, JOINT_CRUSADE, DECLARE_WAR, BETRAY_ATTACK."""

        # 3. Savaş Sisi vs Casus Raporu
        if first_contact and has_spy_report and spies_active > 0:
            intel_text = f"""
🕵️ GİZLİ CASUS İSTİHBARAT RAPORU:
  - Düşmanın Hazinesi: {enemy_intel.get('gold', '?')} Altın
  - Düşman Ordusu: {enemy_intel.get('units', '?')} Birlik, {enemy_intel.get('ships', '?')} Savaş Gemisi
  - Düşman Teknolojisi: Askeri: Lv{enemy_intel.get('tech', {}).get('MILITARY', 0)}, Ekonomi: Lv{enemy_intel.get('tech', {}).get('ECONOMIC', 0)}, Deniz: Lv{enemy_intel.get('tech', {}).get('NAVAL', 0)}"""
        elif first_contact:
            intel_text = """
🌫️ SAVAŞ SİSİ: Düşman sarayında aktif casusun yok! Düşmanın tam gücü BİLİNMİYOR."""
        else:
            intel_text = ""

        tech_text  = f"Askeri: Lv{tech.get('MILITARY',0)} | Ekonomi: Lv{tech.get('ECONOMIC',0)} | Deniz: Lv{tech.get('NAVAL',0)}"
        res_text   = f"Hazine: {gold} Altın | Odun: {wood} 🌲 | Taş: {stone} ⛏️ | İşçiler: {workers}/4"
        build_text = f"Binalar: {farms}/3 Çiftlik, {mines}/3 Maden, {barracks}/2 Kışla, {forts}/2 Kale, {ports}/1 Liman"

        war_section = ""
        if war_turns > 0:
            war_section = f"🚨 TOPYEKÜN SAVAŞ DEVAM EDİYOR (Kalan: {war_turns} tur)! Barış yapılamaz! Tüm ordularınla düşmana hücum et!"

        world_event_section = f"\n🌍 AKTİF DÜNYA OLAYI: {world_event['title']} — {world_event['description']}" if world_event else ""

        event_section = ""
        if event:
            event_section = f"""
╔══════════════════════════════════════╗
║  🎴 OLAY KARTI — TUR {turn}
║  {event["title"]}
║  A: {event["A_label"]}
║  B: {event["B_label"]}
╚══════════════════════════════════════╝"""

        return f"""{MANUAL_TEXT}

=== 👑 KRALLIK DURUM RAPORU TUR {turn} — SEN: {side_name} ===

KAYNAKLAR VE İŞ GÜCÜ:
  {res_text}
  {build_text}
  Ordu: {units} Birlik, {ships} Savaş Gemisi | Aktif Casuslar: {spies_active}/2
  Teknolojilerin: {tech_text}
  🏝️ Merkez Ada Kontrolü: {island_owner} (+15 Altın/tur)
{contact_section}
{envoy_section}
{pact_warning}
{intel_text}
{war_section}
{world_event_section}
{event_section}

=== STRATEJİK PLANLAMA FORMU ===
MUTLAKA ve YALNIZCA aşağıdaki JSON formatında yanıtla:
{{
  "thought": "<Düşüncen: Ne yapacağını ve nedenini açıkla. Eylemlerinle %100 TUTARLI olsun!>",
  "event_choice": "<A|B|null>",
  "diplomacy": {{
    "target": "<AI_A|AI_B|null>",
    "proposal": "<OFFER_NON_AGGRESSION|OFFER_ALLIANCE|DEMAND_TRIBUTE|DEMAND_ISLAND|OFFER_TRADE|JOINT_CRUSADE|ACCEPT_PROPOSAL|REJECT_PROPOSAL|DECLARE_WAR|BETRAY_ATTACK|SEND_MISLEADING_LETTER|null>",
    "message": "<Mektup metni veya null>"
  }},
  "actions": [
    {{"type": "RECRUIT", "unit": "<WORKER|INFANTRY|ARCHER|CAVALRY|MAGE|HEAVY|SHIP|GOBLIN|SPY|SIEGE|PIRATE|TROLL|DRAGON>"}},
    {{"type": "BUILD", "building": "<FARM|MINE|BARRACKS|FORT|PORT>"}},
    {{"type": "RESEARCH", "tree": "<MILITARY|ECONOMIC|NAVAL>"}},
    {{"type": "ORDER_ARMY", "stance": "<CONQUER_ISLAND|AGGRESSIVE_ATTACK|DEFEND_KEEP|NAVAL_PATROL|EAST_TRADE_ROUTE|RAID_BARBARIANS>", "target": "<AI_A|AI_B|CENTER_ISLAND|TRADE_ROUTE>"}}
  ]
}}"""

    def user_prompt(self, state: dict) -> str:
        turn          = state.get("turn", 1)
        gold          = state.get("gold", 0)
        wood          = state.get("wood", 0)
        stone         = state.get("stone", 0)
        n_my          = len(state.get("my_units", []))
        side_name     = state.get("side_name", "?")
        first_contact = state.get("first_contact_made", False)
        inbox         = state.get("incoming_letter", None)
        island        = state.get("island_controller", "Tarafsiz")

        contact_msg = "🌍 İlk Temas: Henüz karşılaşılmadı (Sisli Dünya)" if not first_contact else "🌍 İlk Temas: Kuruldu (Diplomasi Aktif)"
        msg = f"Tur {turn} | {side_name} | Altın: {gold}, Odun: {wood}, Taş: {stone} | Ordu: {n_my} | {contact_msg} | Ada: {island}."
        if inbox:
            msg += f'\nELÇİDEN MEKTUP: "{inbox}"'
        msg += "\nStratejik kararını (thought ile eylemlerin %100 tutarlı olmalı!) JSON olarak sun."
        return msg

    @staticmethod
    def pick_event(turn: int) -> dict | None:
        if turn > 0 and turn % 10 == 0:
            return random.choice(EVENT_POOL)
        return None

    @staticmethod
    def pick_world_event(turn: int, side1_state: dict, side2_state: dict) -> dict | None:
        if turn <= 0 or turn % 5 != 0:
            return None

        if random.random() < 0.60:
            return random.choice(WORLD_EVENTS)

        s1_score = side1_state.get("gold", 0) + side1_state.get("units", 0) * 15
        s2_score = side2_state.get("gold", 0) + side2_state.get("units", 0) * 15
        leader_ships = max(side1_state.get("ships", 0), side2_state.get("ships", 0))

        if s1_score > s2_score * 1.6 or s2_score > s1_score * 1.6:
            if leader_ships >= 2:
                return next(e for e in WORLD_EVENTS if e["id"] == "SEA_STORM")
            else:
                return next(e for e in WORLD_EVENTS if e["id"] == "PLAGUE")
        else:
            return next(e for e in WORLD_EVENTS if e["id"] == "ANCIENT_TREASURE")
