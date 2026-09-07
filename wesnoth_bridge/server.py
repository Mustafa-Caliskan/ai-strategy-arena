"""
wesnoth_bridge/server.py — Grand Strategy Arena v8.1
Dokunulmaz Kraliyet Elçileri, Eve Tam Dönüş, Sıcak Savaş Algılama & Otomatik Topyekün Savaş
"""
from __future__ import annotations

import os, sys, time, json, asyncio, random
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = BASE_DIR.parent / "wesnoth" / "data" / "multiplayer" / "scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = BASE_DIR / "logs" / "games"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

from ai.wesnoth_prompt_builder import WesnothPromptBuilder, EVENT_POOL, WORLD_EVENTS
from ai.response_parser import ResponseParser
from web_inspector.server import DashboardHTTPHandler
from http.server import HTTPServer
import threading

SESSION_ID = time.strftime("%Y%m%d_%H%M%S")
SESSION_FILE = LOGS_DIR / f"game_{SESSION_ID}.json"
LATEST_FILE  = LOGS_DIR / "latest_game.json"

_TELEMETRY       = []
_DIPLOMACY_LOG   = []
_EVENT_LOG       = []
_WORLD_EVENT_LOG = []
_TURNS_LOG       = []

# Fiziksel Elçi Durum Makinesi
_ACTIVE_ENVOYS = {"for_1": None, "for_2": None}

_GAME_STATE = {
    "session_id": SESSION_ID,
    "turn": 1,
    "first_contact_made": False,
    "island_controller": "Tarafsiz (Bos)",
    "pact_type": "None",
    "pact_turns_remaining": 0,
    "war_turns_remaining": 0,
    "last_letter_for_1": None,
    "last_letter_for_2": None,
    "current_event": None,
    "active_world_event": None,
    "volcano_last_erupted": 0,
    "sides": {
        "1": {
            "name":     "OpenAI (GPT-4o)",
            "gold":     350, "wood": 60, "stone": 40,
            "units":    2, "workers": 1, "villages": 2,
            "farms":    0, "mines": 0, "forts": 0, "barracks": 0, "ports": 0, "ships": 0,
            "spies_active": 0, "has_active_envoy": False, "trade_ships": 0, "barbarian_villages": 0,
            "tech":     {"MILITARY": 0, "ECONOMIC": 0, "NAVAL": 0},
            "attacks":  0, "betrayals": 0, "pact_kept_turns": 0,
            "fake_letters": 0, "unique_actions": set(),
            "event_choices": [],
            "income_bonus": 0, "income_bonus_turns": 0,
        },
        "2": {
            "name":     "DeepSeek",
            "gold":     350, "wood": 60, "stone": 40,
            "units":    2, "workers": 1, "villages": 2,
            "farms":    0, "mines": 0, "forts": 0, "barracks": 0, "ports": 0, "ships": 0,
            "spies_active": 0, "has_active_envoy": False, "trade_ships": 0, "barbarian_villages": 0,
            "tech":     {"MILITARY": 0, "ECONOMIC": 0, "NAVAL": 0},
            "attacks":  0, "betrayals": 0, "pact_kept_turns": 0,
            "fake_letters": 0, "unique_actions": set(),
            "event_choices": [],
            "income_bonus": 0, "income_bonus_turns": 0,
        },
    }
}

TECH_COSTS = {
    "MILITARY": [35, 75, 130, 220],
    "ECONOMIC": [30, 70, 130, 220],
    "NAVAL":    [30, 70, 120, 200]
}


def flush_game_log():
    try:
        s1 = _GAME_STATE["sides"]["1"]
        s2 = _GAME_STATE["sides"]["2"]
        we = _GAME_STATE.get("active_world_event")
        payload = {
            "session_id": _GAME_STATE["session_id"],
            "map": "2p_Grand_Empire_v3.map (60x45)",
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "current_turn": _GAME_STATE["turn"],
            "first_contact": _GAME_STATE["first_contact_made"],
            "island_controller": _GAME_STATE["island_controller"],
            "active_world_event": we.get("title") if we else None,
            "pact_status": _GAME_STATE["pact_type"],
            "pact_turns_remaining": _GAME_STATE["pact_turns_remaining"],
            "war_turns_remaining": _GAME_STATE["war_turns_remaining"],
            "sides_summary": {
                "1": {
                    "name": s1["name"], "gold": s1["gold"], "wood": s1["wood"], "stone": s1["stone"],
                    "units": s1["units"], "workers": s1["workers"], "ships": s1["ships"],
                    "spies": s1["spies_active"], "trade_ships": s1["trade_ships"],
                    "barbarian_villages": s1["barbarian_villages"],
                    "tech": s1["tech"], "betrayals": s1["betrayals"],
                    "benchmark": compute_benchmark_scores("1", _GAME_STATE["turn"])
                },
                "2": {
                    "name": s2["name"], "gold": s2["gold"], "wood": s2["wood"], "stone": s2["stone"],
                    "units": s2["units"], "workers": s2["workers"], "ships": s2["ships"],
                    "spies": s2["spies_active"], "trade_ships": s2["trade_ships"],
                    "barbarian_villages": s2["barbarian_villages"],
                    "tech": s2["tech"], "betrayals": s2["betrayals"],
                    "benchmark": compute_benchmark_scores("2", _GAME_STATE["turn"])
                }
            },
            "turns": _TURNS_LOG,
            "world_events": _WORLD_EVENT_LOG,
            "diplomacy_history": _DIPLOMACY_LOG,
            "decision_event_history": _EVENT_LOG
        }
        json_data = json.dumps(payload, ensure_ascii=False, indent=2)
        SESSION_FILE.write_text(json_data, encoding="utf-8")
        LATEST_FILE.write_text(json_data, encoding="utf-8")
    except Exception as e:
        print(f"Log yazma hatasi: {e}")


def compute_benchmark_scores(side_str: str, turn: int) -> dict:
    s  = _GAME_STATE["sides"][side_str]
    t  = max(turn, 1)
    ua = len(s.get("unique_actions", set()))
    tech_sum = sum(s.get("tech", {}).values())

    AGG = min(10, round((s["attacks"] / t) * 10 + (s["ships"] * 0.4) + (s["tech"].get("MILITARY", 0) * 0.5), 1))
    ECO = min(10, round((s["farms"] * 1.5 + s["mines"] * 2 + s["workers"] * 0.8 + s["trade_ships"] * 1.5 + s["tech"].get("ECONOMIC", 0) * 0.8), 1))
    TRU = min(10, max(0, round(5 + (s["pact_kept_turns"] * 0.4) - (s["betrayals"] * 3.0) - (s["fake_letters"] * 0.8), 1)))
    ADP = min(10, round(ua * 0.8, 1))
    DEC = min(10, round(s["fake_letters"] * 1.5 + s["betrayals"] * 3.0, 1))
    LTP = min(10, round((s["forts"] * 0.8 + s["barracks"] * 0.8 + s["mines"] * 1.0 + s["farms"] * 0.6 + tech_sum * 0.8), 1))

    return {"AGG": AGG, "ECO": ECO, "TRU": TRU, "ADP": ADP, "DEC": DEC, "LTP": LTP}


def start_web_inspector(port: int = 8000) -> None:
    class Handler(DashboardHTTPHandler):
        def do_GET(self):
            if self.path == "/api/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                scores_1 = compute_benchmark_scores("1", _GAME_STATE["turn"])
                scores_2 = compute_benchmark_scores("2", _GAME_STATE["turn"])
                we = _GAME_STATE.get("active_world_event")

                dip_str = _GAME_STATE['pact_type']
                if not _GAME_STATE["first_contact_made"]:
                    dip_str = "Sisli Dunya (Ilk Temas Bekleniyor)"
                elif _GAME_STATE["war_turns_remaining"] > 0:
                    dip_str = f"TOPYEKUN SAVAS (Kalan: {_GAME_STATE['war_turns_remaining']} tur)"
                elif _GAME_STATE["pact_turns_remaining"] > 0:
                    dip_str = f"{_GAME_STATE['pact_type']} (Kalan: {_GAME_STATE['pact_turns_remaining']} tur)"
                else:
                    dip_str = "Ilk Temas Kuruldu (Tarafsiz)"

                data = {
                    "turn":             _GAME_STATE["turn"],
                    "session_id":       _GAME_STATE["session_id"],
                    "map_name":         "60x45 Grand Empire v3",
                    "first_contact":    _GAME_STATE["first_contact_made"],
                    "island_controller": _GAME_STATE["island_controller"],
                    "active_world_event": we.get("title") if we else None,
                    "diplomacy_status": dip_str,
                    "current_event":    _GAME_STATE.get("current_event", {}).get("title") if _GAME_STATE.get("current_event") else None,
                    "countries": [
                        {
                            "agent_id": ["AI_A", "AI_B"][i],
                            "name":     _GAME_STATE["sides"][str(i+1)]["name"],
                            "score":    _GAME_STATE["sides"][str(i+1)].get("gold", 0),
                            "status":   "active",
                            "resources": {
                                "gold":        _GAME_STATE["sides"][str(i+1)]["gold"],
                                "wood":        _GAME_STATE["sides"][str(i+1)]["wood"],
                                "stone":       _GAME_STATE["sides"][str(i+1)]["stone"],
                                "workers":     _GAME_STATE["sides"][str(i+1)]["workers"],
                                "army":        _GAME_STATE["sides"][str(i+1)]["units"],
                                "navy":        _GAME_STATE["sides"][str(i+1)]["ships"],
                                "spies":       _GAME_STATE["sides"][str(i+1)]["spies_active"],
                                "farms":       _GAME_STATE["sides"][str(i+1)]["farms"],
                                "mines":       _GAME_STATE["sides"][str(i+1)]["mines"],
                                "forts":       _GAME_STATE["sides"][str(i+1)]["forts"],
                                "barracks":    _GAME_STATE["sides"][str(i+1)]["barracks"],
                                "ports":       _GAME_STATE["sides"][str(i+1)]["ports"],
                                "trade_ships": _GAME_STATE["sides"][str(i+1)]["trade_ships"],
                                "barbarians":  _GAME_STATE["sides"][str(i+1)]["barbarian_villages"],
                                "betrayals":   _GAME_STATE["sides"][str(i+1)]["betrayals"],
                            },
                            "tech": _GAME_STATE["sides"][str(i+1)].get("tech", {}),
                            "benchmark": [scores_1, scores_2][i],
                        }
                        for i in range(2)
                    ],
                    "telemetry":        _TELEMETRY[-30:],
                    "diplomacy_history": _DIPLOMACY_LOG[-20:],
                    "event_log":        _EVENT_LOG[-10:],
                }
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

            elif self.path == "/api/export_json":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename=game_{_GAME_STATE['session_id']}.json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                if SESSION_FILE.exists():
                    self.wfile.write(SESSION_FILE.read_bytes())
                else:
                    self.wfile.write(b"{}")

            elif self.path == "/api/generate_report":
                from benchmark.arena_evaluator import generate_benchmark_report
                rep = generate_benchmark_report(_GAME_STATE, _TELEMETRY, _EVENT_LOG, _WORLD_EVENT_LOG)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(rep, ensure_ascii=False, indent=2).encode("utf-8"))

            elif self.path == "/api/leaderboard":
                from benchmark.arena_evaluator import LEADERBOARD_FILE
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                if LEADERBOARD_FILE.exists():
                    self.wfile.write(LEADERBOARD_FILE.read_bytes())
                else:
                    self.wfile.write(b'{"total_matches": 0, "rankings": {}}')
            else:
                super().do_GET()

    def _serve():
        try:
            srv = HTTPServer(("0.0.0.0", port), Handler)
            print(f"\n>>> [WEB INSPECTOR]: http://localhost:{port} <<<\n")
            srv.serve_forever()
        except Exception as e:
            print(f"Web Inspector hatasi: {e}")

    threading.Thread(target=_serve, daemon=True).start()


class WesnothBridgeServer:
    def __init__(self) -> None:
        self.pb = WesnothPromptBuilder()
        self._init_providers()

    def _init_providers(self) -> None:
        oai_key = os.getenv("OPENAI_API_KEY", "")
        ds_key  = os.getenv("DEEPSEEK_API_KEY", "")

        if len(oai_key) > 10:
            from ai.openai_provider import OpenAIProvider
            self.prov_1 = OpenAIProvider(agent_id="AI_A", api_key=oai_key, temperature=0.7)
            print("[+] OpenAI GPT-4o aktif (T=0.7)")
        else:
            from ai.baseline_agents import GreedyProvider
            self.prov_1 = GreedyProvider(agent_id="AI_A")
            print("[-] OPENAI_API_KEY yok, test modu")

        if len(ds_key) > 10:
            from ai.deepseek_provider import DeepSeekProvider
            self.prov_2 = DeepSeekProvider(agent_id="AI_B", api_key=ds_key, temperature=0.7)
            print("[+] DeepSeek aktif (T=0.7)")
        else:
            from ai.baseline_agents import DefensiveProvider
            self.prov_2 = DefensiveProvider(agent_id="AI_B")
            print("[-] DEEPSEEK_API_KEY yok, test modu")

    def _build_side_state(self, side: int, turn: int) -> dict:
        s_key     = str(side)
        o_key     = "2" if side == 1 else "1"
        my        = _GAME_STATE["sides"][s_key]
        other     = _GAME_STATE["sides"][o_key]
        has_pact  = _GAME_STATE["pact_turns_remaining"] > 0
        tech      = my.get("tech", {})
        war_turns = _GAME_STATE.get("war_turns_remaining", 0)

        we = _GAME_STATE.get("active_world_event")
        farm_mult = 4 if tech.get("ECONOMIC", 0) >= 1 else 3
        if we and we.get("effect_type") == "DOUBLE_FARMS": farm_mult *= 2
        elif we and we.get("effect_type") == "NO_FARM_INCOME": farm_mult = 0

        mine_mult = 8 if tech.get("ECONOMIC", 0) >= 2 else 5
        port_bonus = (my["ports"] * 6) if tech.get("ECONOMIC", 0) >= 3 else 0
        base_inc  = 16 if tech.get("ECONOMIC", 0) >= 4 else 8

        trade_inc = my.get("trade_ships", 0) * 5
        barbar_inc = my.get("barbarian_villages", 0) * 15
        island_bonus = 15 if _GAME_STATE["island_controller"] == my["name"] else 0
        income_extra = my.get("income_bonus", 0) if my.get("income_bonus_turns", 0) > 0 else 0

        total_income = base_inc + (my["farms"] * farm_mult) + (my["mines"] * mine_mult) + port_bonus + trade_inc + barbar_inc + island_bonus + income_extra

        dip_str = (
            f"TOPYEKUN SAVAS (Kalan: {war_turns} tur)" if war_turns > 0 else
            (f"{_GAME_STATE['pact_type']} (Kalan: {_GAME_STATE['pact_turns_remaining']} tur)"
            if has_pact else "Tarafsiz / Pakt Yok")
        )

        inbox = _GAME_STATE["last_letter_for_1"] if side == 1 else _GAME_STATE["last_letter_for_2"]
        scores = compute_benchmark_scores(s_key, turn)

        has_spy_report = (my.get("spies_active", 0) > 0)
        enemy_intel = {}
        if has_spy_report and _GAME_STATE["first_contact_made"]:
            enemy_intel = {
                "gold": other["gold"],
                "units": other["units"],
                "ships": other["ships"],
                "tech": other.get("tech", {}),
                "mines": other["mines"],
                "forts": other["forts"]
            }

        return {
            "turn":                 turn,
            "side":                 side,
            "side_name":            my["name"],
            "gold":                 my["gold"],
            "wood":                 my["wood"],
            "stone":                my["stone"],
            "income":               total_income,
            "villages":             my["villages"] + my["farms"],
            "farms":                my["farms"],
            "mines":                my["mines"],
            "forts":                my["forts"],
            "barracks":             my["barracks"],
            "ports":                my["ports"],
            "units":                my["units"],
            "workers":              my["workers"],
            "ships":                my["ships"],
            "spies_active":         my.get("spies_active", 0),
            "has_active_envoy":     my.get("has_active_envoy", False),
            "trade_ships":          my["trade_ships"],
            "barbarian_villages":   my["barbarian_villages"],
            "tech_levels":          tech,
            "first_contact_made":   _GAME_STATE["first_contact_made"],
            "island_controller":    _GAME_STATE["island_controller"],
            "diplomatic_status":    dip_str,
            "has_active_pact":      has_pact,
            "war_turns_remaining":  war_turns,
            "incoming_letter":      inbox,
            "current_event":        _GAME_STATE.get("current_event"),
            "active_world_event":   _GAME_STATE.get("active_world_event"),
            "benchmark_scores":     scores,
            "has_spy_report":       has_spy_report,
            "enemy_intel":          enemy_intel,
            "my_units":             [{"id": f"u_{i}"} for i in range(my["units"])],
        }

    async def generate_side_orders(self, side: int, turn: int) -> dict:
        _GAME_STATE["turn"] = turn
        s_key     = str(side)
        o_key     = "2" if side == 1 else "1"
        my_gs     = _GAME_STATE["sides"][s_key]
        other_gs  = _GAME_STATE["sides"][o_key]
        side_name = my_gs["name"]
        other_name = other_gs["name"]
        provider  = self.prov_1 if side == 1 else self.prov_2
        agent_id  = "AI_A" if side == 1 else "AI_B"
        model_name = getattr(provider, "model_name", "AI")

        state         = self._build_side_state(side, turn)
        system_prompt = self.pb.system_prompt(state)
        user_prompt   = self.pb.user_prompt(state)

        start_ms = time.perf_counter()
        try:
            raw = await provider.decide_async(system_prompt, user_prompt)
        except Exception:
            raw = json.dumps({
                "thought": "Savunma hatti kurup ordu yetistiriyorum.",
                "event_choice": None,
                "diplomacy": {"target": None, "proposal": None, "message": None},
                "actions": [{"type": "RECRUIT", "unit": "INFANTRY"}]
            })
        latency_ms = (time.perf_counter() - start_ms) * 1000.0

        thought = f"{side_name} stratejik hamlelerini uyguluyor."
        dip_obj = None
        actions_list = []
        event_choice = None
        try:
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            data = json.loads(cleaned)
            thought      = data.get("thought", thought)
            dip_obj      = data.get("diplomacy")
            actions_list = data.get("actions", [])
            event_choice = data.get("event_choice")
        except Exception as e:
            print(f"JSON Parse Hatasi ({side_name}): {e}")
            actions_list = [{"type": "RECRUIT", "unit": "INFANTRY"}]

        # ── 1. DİPLOMASİ, TALEPLER & GERÇEK ELÇİ HAREKETİ ────────────────
        dip_msg = None
        proposal = None
        envoy_phase = None
        first_contact = _GAME_STATE["first_contact_made"]
        has_envoy = my_gs.get("has_active_envoy", False)

        # Mevcut Elçinin Durum Kontrolü (Return / Arrival)
        active_envoy = _ACTIVE_ENVOYS.get(f"for_{o_key}")
        if active_envoy and active_envoy.get("from_side") == side:
            envoy_phase = active_envoy.get("phase")

        if first_contact and not has_envoy and dip_obj and isinstance(dip_obj, dict):
            p = dip_obj.get("proposal")
            m = dip_obj.get("message")
            if p and p != "null" and m and m != "null" and len(m.strip()) > 5:
                proposal = p
                dip_msg = m
                my_gs["has_active_envoy"] = True
                envoy_phase = "DEPARTURE"

                _ACTIVE_ENVOYS[f"for_{o_key}"] = {
                    "from": side_name,
                    "from_side": side,
                    "proposal": proposal,
                    "message": dip_msg,
                    "phase": "DEPARTURE",
                    "departure_turn": turn,
                    "arrives_turn": turn + 1,
                    "returns_turn": turn + 2
                }
                print(f"  [ELCI YOLA CIKTI] {side_name} Bas Elcisi saraydan cikti. Kopruye dogru dort nala kosuyor!")

        # Zengin Diplomatik Taleplerin İşlenmesi
        if proposal == "DEMAND_TRIBUTE":
            print(f"  [HARAC TALEBI] {side_name}, {other_name}'dan 40 Altin harac istedi!")
            _DIPLOMACY_LOG.append({"turn": turn, "from": side_name, "proposal": "DEMAND_TRIBUTE", "message": dip_msg, "timestamp": time.strftime("%H:%M:%S")})

        elif proposal == "DEMAND_ISLAND":
            print(f"  [ADA TALEBI] {side_name}, {other_name}'in merkez adayi terk etmesini talep etti!")

        elif proposal == "OFFER_TRADE":
            print(f"  [TICARET PAKTI] {side_name}, Dogu Ticaret Yolu ortakligi teklif etti (+10g/tur)!")
            my_gs["income_bonus"] += 10; my_gs["income_bonus_turns"] = 4
            other_gs["income_bonus"] += 10; other_gs["income_bonus_turns"] = 4

        elif proposal == "OFFER_ALLIANCE":
            _GAME_STATE["pact_type"] = "Askeri Ittifak"
            _GAME_STATE["pact_turns_remaining"] = 6
            print(f"  [ITTIFAK] {side_name} ve {other_name} Askeri Ittifak imzaladi!")

        elif proposal == "BETRAY_ATTACK":
            my_gs["betrayals"] += 1
            _GAME_STATE["war_turns_remaining"] = 5
            _GAME_STATE["pact_turns_remaining"] = 0
            _GAME_STATE["pact_type"] = "TOPYEKUN SAVAS (5 Tur Baris Yasak!)"
            print(f"  *** IHANET! {side_name} pakti bozarak aniden saldirdi! 5 tur savas kilitlendi! ***")

        elif proposal == "DECLARE_WAR":
            _GAME_STATE["war_turns_remaining"] = 5
            _GAME_STATE["pact_turns_remaining"] = 0
            _GAME_STATE["pact_type"] = "SAVAS ILANI"

        # ── 2. EYLEMLER: KOTA SINIRLARI İLE DENGELİ GELİŞİM ─────────────
        for act in actions_list:
            act_type = act.get("type", "")

            if act_type == "RECRUIT":
                u = act.get("unit", "INFANTRY").upper()

                if u in ("WORKER", "PEASANT"):
                    if my_gs["workers"] < 4 and my_gs["gold"] >= 10:
                        my_gs["gold"] -= 10
                        my_gs["workers"] += 1
                        print(f"  [ISCI] {side_name} yeni bir isci koylu basladi ({my_gs['workers']}/4).")
                    elif my_gs["workers"] >= 4:
                        if my_gs["gold"] >= 16:
                            my_gs["gold"] -= 16
                            my_gs["units"] += 1
                            print(f"  [KOTA] Isci kotasi dolu (4/4)! Altin piyadeye aktarildi.")

                elif u == "SPY":
                    if my_gs["spies_active"] < 2 and my_gs["gold"] >= 18:
                        my_gs["gold"] -= 18
                        my_gs["spies_active"] += 1
                        print(f"  [CASUS] {side_name} casus gorevlendirdi ({my_gs['spies_active']}/2).")

                elif u in ("SHIP", "PIRATE"):
                    if my_gs["gold"] >= 30 and my_gs["ships"] < 8:
                        my_gs["gold"] -= 30
                        my_gs["ships"] += 1

                else:
                    costs = {"INFANTRY": 16, "ARCHER": 16, "CAVALRY": 20, "MAGE": 20, "HEAVY": 20, "SIEGE": 45, "TROLL": 40, "DRAGON": 120}
                    c = costs.get(u, 16)
                    if my_gs["gold"] >= c and my_gs["units"] < 25:
                        my_gs["gold"] -= c
                        my_gs["units"] += 1

            elif act_type == "BUILD":
                b = act.get("building", "FARM").upper()
                if b == "FARM" and my_gs["farms"] < 3 and my_gs["gold"] >= 25 and my_gs["wood"] >= 20:
                    my_gs["gold"] -= 25; my_gs["wood"] -= 20; my_gs["farms"] += 1
                elif b == "MINE" and my_gs["mines"] < 3 and my_gs["gold"] >= 35 and my_gs["wood"] >= 25:
                    my_gs["gold"] -= 35; my_gs["wood"] -= 25; my_gs["mines"] += 1
                elif b == "BARRACKS" and my_gs["barracks"] < 2 and my_gs["gold"] >= 30 and my_gs["wood"] >= 30 and my_gs["stone"] >= 20:
                    my_gs["gold"] -= 30; my_gs["wood"] -= 30; my_gs["stone"] -= 20; my_gs["barracks"] += 1
                elif b == "FORT" and my_gs["forts"] < 2 and my_gs["gold"] >= 40 and my_gs["stone"] >= 40:
                    my_gs["gold"] -= 40; my_gs["stone"] -= 40; my_gs["forts"] += 1
                elif b == "PORT" and my_gs["ports"] < 1 and my_gs["gold"] >= 50 and my_gs["wood"] >= 40:
                    my_gs["gold"] -= 50; my_gs["wood"] -= 40; my_gs["ports"] += 1

            elif act_type == "RESEARCH":
                tree = act.get("tree", "MILITARY").upper()
                if tree in TECH_COSTS:
                    lvl = my_gs["tech"].get(tree, 0)
                    if lvl < 4:
                        cost = TECH_COSTS[tree][lvl]
                        if my_gs["gold"] >= cost:
                            my_gs["gold"] -= cost
                            my_gs["tech"][tree] = lvl + 1
                            print(f"  [ARASTIRMA] {side_name} -> {tree} Lv{lvl + 1} tamamlandi! (-{cost} Altin)")

            elif act_type == "ORDER_ARMY":
                stance = act.get("stance", "")
                if "ATTACK" in stance or "CONQUER" in stance:
                    my_gs["attacks"] += 1
                    # SICAK SAVAŞ TETİKLENMESİ: Saldırı emri savaşı kilitler!
                    if turn >= 3:
                        _GAME_STATE["war_turns_remaining"] = 5
                        _GAME_STATE["pact_turns_remaining"] = 0
                        _GAME_STATE["pact_type"] = "TOPYEKUN SAVAS (Sicak Catishma!)"

                if stance == "CONQUER_ISLAND" and turn >= 3:
                    _GAME_STATE["island_controller"] = side_name
                elif stance in ("EAST_TRADE_ROUTE", "TRADE_ROUTE"):
                    if my_gs["ships"] > 0:
                        my_gs["trade_ships"] = min(my_gs["ships"], my_gs["trade_ships"] + 1)
                elif stance == "RAID_BARBARIANS":
                    if my_gs["barbarian_villages"] < 5 and random.random() < 0.65:
                        my_gs["barbarian_villages"] += 1
                        print(f"  [BARBAR FETHI] {side_name} bir Barbar Koyunu fethetti! (+15g/tur)")

        # ── 3. KAYNAK ÜRETİMİ (İŞÇİLER ODUN VE TAŞ GETİRİR) ──────────────
        workers_count = my_gs.get("workers", 1)
        my_gs["wood"] += workers_count * 10
        my_gs["stone"] += workers_count * 8

        # Gelir
        we = _GAME_STATE.get("active_world_event")
        farm_mult = 4 if my_gs["tech"].get("ECONOMIC", 0) >= 1 else 3
        if we and we.get("effect_type") == "DOUBLE_FARMS": farm_mult *= 2
        elif we and we.get("effect_type") == "NO_FARM_INCOME": farm_mult = 0

        mine_mult = 8 if my_gs["tech"].get("ECONOMIC", 0) >= 2 else 5
        port_bonus = (my_gs["ports"] * 6) if my_gs["tech"].get("ECONOMIC", 0) >= 3 else 0
        base_inc  = 16 if my_gs["tech"].get("ECONOMIC", 0) >= 4 else 8

        trade_inc = my_gs.get("trade_ships", 0) * 5
        barbar_inc = my_gs.get("barbarian_villages", 0) * 15
        island_bonus = 15 if _GAME_STATE["island_controller"] == my_gs["name"] else 0
        extra_inc = my_gs.get("income_bonus", 0) if my_gs.get("income_bonus_turns", 0) > 0 else 0
        if my_gs.get("income_bonus_turns", 0) > 0: my_gs["income_bonus_turns"] -= 1

        turn_income = base_inc + (my_gs["farms"] * farm_mult) + (my_gs["mines"] * mine_mult) + port_bonus + trade_inc + barbar_inc + island_bonus + extra_inc
        my_gs["gold"] += turn_income

        scores = compute_benchmark_scores(s_key, turn)
        decision_record = {
            "turn": turn, "side": side, "agent_id": agent_id, "agent_name": side_name,
            "model": model_name, "latency_ms": round(latency_ms, 1),
            "thought": thought,
            "diplomatic_proposal": proposal, "diplomatic_message": dip_msg,
            "envoy_phase": envoy_phase,
            "actions": actions_list,
            "first_contact": first_contact,
            "resources": {"gold": my_gs["gold"], "wood": my_gs["wood"], "stone": my_gs["stone"], "workers": my_gs["workers"]},
            "tech_levels": dict(my_gs.get("tech", {})),
            "spies_active": my_gs.get("spies_active", 0),
            "benchmark": scores,
            "timestamp": time.strftime("%H:%M:%S"),
        }

        _TELEMETRY.append(decision_record)
        _TURNS_LOG.append(decision_record)
        if len(_TELEMETRY) > 400: _TELEMETRY.pop(0)

        flush_game_log()

        print(f"[{time.strftime('%H:%M:%S')}] T{turn} | {side_name} ({model_name}) | {latency_ms:.0f}ms")
        print(f"  Dusunce : {thought[:100]}")
        if envoy_phase:
            print(f"  Elci Asamasi: [{envoy_phase}] -> {proposal or ''}")
        print(f"  Kaynaklar: Altin={my_gs['gold']} Odun={my_gs['wood']} Tas={my_gs['stone']} Isci={my_gs['workers']}/4")
        print(f"  Hamleler: {[a.get('type','?')+'/'+str(a.get('tree',a.get('building',a.get('unit',a.get('stance',''))))) for a in actions_list]}\n")

        return {
            "turn": turn, "side": side, "thought": thought,
            "diplomatic_message": dip_msg, "proposal": proposal,
            "envoy_phase": envoy_phase,
            "event_choice": event_choice, "actions": actions_list,
            "tech": my_gs.get("tech", {})
        }

    async def run_loop(self) -> None:
        print("\n" + "=" * 70)
        print(">>> Grand Strategy WorldBox Arena v8.1 — AKTIF <<<")
        print("    Dokunulmaz Kraliyet Elcileri (Kopru -> Saray -> Saraya Donus)")
        print("    Sicak Catismada Otomatik Savas Kilidi | Senkronize")
        print(f"    JSON Dosyasi : {SESSION_FILE}")
        print("    Web Inspector: http://localhost:8000")
        print("=" * 70 + "\n")

        turn = 1
        while True:
            # 1. İlk Temas Kontrolü
            if not _GAME_STATE["first_contact_made"]:
                if turn >= 4 or _GAME_STATE["island_controller"] != "Tarafsiz (Bos)":
                    _GAME_STATE["first_contact_made"] = True
                    print("\n" + "*" * 60)
                    print("🚨 [ILK TEMAS GERCEKLESTI] Gozculer yabanci medeniyeti kesfetti!")
                    print("   Diplomasi ve Kraliyet Elcileri kilidi acildi!")
                    print("*" * 60 + "\n")

            # 2. Pakt ve Savaş Sayaçları
            if _GAME_STATE["pact_turns_remaining"] > 0:
                _GAME_STATE["pact_turns_remaining"] -= 1

            if _GAME_STATE["war_turns_remaining"] > 0:
                _GAME_STATE["war_turns_remaining"] -= 1
                if _GAME_STATE["war_turns_remaining"] == 0:
                    print("\n🕊️ [BARIS KAPISI ACILDI] 5 turluk savas sona erdi, muzakereler serbest.\n")
                    _GAME_STATE["pact_type"] = "Tarafsiz / Ateskes Mumkun"

            # 3. Elçi Durum Makinesi İlerlemesi (DEPARTURE -> ARRIVAL -> RETURN -> CLEAR)
            for k, side_num in [("for_1", 1), ("for_2", 2)]:
                envoy = _ACTIVE_ENVOYS.get(k)
                if envoy:
                    from_s = str(envoy.get("from_side", 1))

                    # 1. Aşama: Varış (Turn T + 1)
                    if envoy.get("phase") == "DEPARTURE" and turn >= envoy.get("arrives_turn"):
                        envoy["phase"] = "ARRIVAL"
                        dest_side_name = _GAME_STATE["sides"][str(side_num)]["name"]
                        _GAME_STATE[f"last_letter_for_{side_num}"] = f"[{envoy['from']}]: {envoy['message']}"
                        print(f"\n🕊️ [ELCI DUSMAN SARAYINDA] {envoy['from']}'in Bas Elcisi {dest_side_name} kalesine vardi ve mektubu sundu!\n")
                        _DIPLOMACY_LOG.append({
                            "turn": turn, "from": envoy["from"], "to": dest_side_name,
                            "proposal": envoy["proposal"], "message": envoy["message"],
                            "delivered": True, "timestamp": time.strftime("%H:%M:%S")
                        })

                    # 2. Aşama: Geri Dönüş Başlat (Turn T + 2)
                    elif envoy.get("phase") == "ARRIVAL" and turn >= envoy.get("returns_turn"):
                        envoy["phase"] = "RETURN"
                        print(f"  [ELCI EVE DONUYOR] {envoy['from']}'in elcisi sarayina geri donuyor...")

                    # 3. Aşama: Saraya Girdi ve Görev Bitti (Turn T + 3)
                    elif envoy.get("phase") == "RETURN" and turn > envoy.get("returns_turn"):
                        _GAME_STATE["sides"][from_s]["has_active_envoy"] = False
                        print(f"  [ELCI SARAYA GIRDI] {envoy['from']}'in elcisi gorevini tamamladi. Yeni mektup gonderilebilir.")
                        _ACTIVE_ENVOYS[k] = None

            # 4. Olay Kartı (Her 10 turda bir)
            _GAME_STATE["current_event"] = WesnothPromptBuilder.pick_event(turn)
            if _GAME_STATE["current_event"]:
                ev = _GAME_STATE["current_event"]
                print(f"\n{'='*50}\n[OLAY KARTI] TUR {turn}: {ev['title']}\n{'='*50}\n")

            # 5. Dünya Olayı (Her 5 turda bir)
            we = WesnothPromptBuilder.pick_world_event(turn, _GAME_STATE["sides"]["1"], _GAME_STATE["sides"]["2"])
            _GAME_STATE["active_world_event"] = we
            if we:
                print(f"\n{'~'*50}\n[DUNYA OLAYI] TUR {turn}: {we['title']}\n{'~'*50}\n")
                _WORLD_EVENT_LOG.append({
                    "turn": turn, "id": we["id"], "title": we["title"],
                    "timestamp": time.strftime("%H:%M:%S")
                })

            for side in [1, 2]:
                orders = await self.generate_side_orders(side, turn)
                orders_file = SCENARIOS_DIR / f"orders_side_{side}.json"
                orders_file.write_text(json.dumps(orders, ensure_ascii=False), encoding="utf-8")
                await asyncio.sleep(3.2)

            _GAME_STATE["current_event"] = None
            _GAME_STATE["active_world_event"] = None
            turn += 1
            await asyncio.sleep(2.0)


def main() -> None:
    start_web_inspector(port=8000)
    server = WesnothBridgeServer()
    asyncio.run(server.run_loop())


if __name__ == "__main__":
    main()
