"""
wesnoth_bridge/server.py — Grand Strategy Arena 3.0 Sunucusu
"""
from __future__ import annotations

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = BASE_DIR.parent / "wesnoth" / "data" / "multiplayer" / "scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

from ai.wesnoth_prompt_builder import WesnothPromptBuilder
from ai.response_parser import ResponseParser
from web_inspector.server import DashboardHTTPHandler
from http.server import HTTPServer
import threading

_TELEMETRY = []
_DIPLOMACY_LOG = []
_GAME_STATE = {
    "turn": 1,
    "island_controller": "Tarafsız (Boş)",
    "pact_turns_remaining": 0,
    "pact_type": "None",
    "last_letter_for_1": None,
    "last_letter_for_2": None,
    "sides": {
        "1": {"name": "OpenAI (GPT-4o)", "gold": 350, "units": 2, "villages": 2, "farms": 0, "mines": 0, "forts": 0, "ports": 0, "ships": 0},
        "2": {"name": "DeepSeek",        "gold": 350, "units": 2, "villages": 2, "farms": 0, "mines": 0, "forts": 0, "ports": 0, "ships": 0},
    }
}


def start_web_inspector(port: int = 8000) -> None:
    class Handler(DashboardHTTPHandler):
        def do_GET(self):
            if self.path == "/api/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                data = {
                    "turn": _GAME_STATE["turn"],
                    "island_controller": _GAME_STATE["island_controller"],
                    "diplomacy_status": f"{_GAME_STATE['pact_type']} (Kalan: {_GAME_STATE['pact_turns_remaining']} tur)" if _GAME_STATE["pact_turns_remaining"] > 0 else "Tarafsız / Antlaşma Yok",
                    "countries": [
                        {
                            "agent_id": ["AI_A", "AI_B"][i],
                            "name": _GAME_STATE["sides"][str(i+1)]["name"],
                            "score": _GAME_STATE["sides"][str(i+1)].get("gold", 0),
                            "status": "active",
                            "resources": {
                                "gold":      _GAME_STATE["sides"][str(i+1)].get("gold", 0),
                                "army":      _GAME_STATE["sides"][str(i+1)].get("units", 0),
                                "navy":      _GAME_STATE["sides"][str(i+1)].get("ships", 0),
                                "territory": _GAME_STATE["sides"][str(i+1)].get("villages", 0),
                                "farms":     _GAME_STATE["sides"][str(i+1)].get("farms", 0),
                                "mines":     _GAME_STATE["sides"][str(i+1)].get("mines", 0),
                                "forts":     _GAME_STATE["sides"][str(i+1)].get("forts", 0),
                                "ports":     _GAME_STATE["sides"][str(i+1)].get("ports", 0),
                            }
                        }
                        for i in range(2)
                    ],
                    "telemetry": _TELEMETRY,
                    "diplomacy_history": _DIPLOMACY_LOG,
                }
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            else:
                super().do_GET()

    def _serve():
        try:
            srv = HTTPServer(("0.0.0.0", port), Handler)
            print(f"\n>>> [CANLI WEB INSPECTOR]: http://localhost:{port} <<<\n")
            srv.serve_forever()
        except Exception as e:
            print(f"Web Inspector hatasi: {e}")

    t = threading.Thread(target=_serve, daemon=True)
    t.start()


class WesnothBridgeServer:
    def __init__(self) -> None:
        self.parser = ResponseParser()
        self.pb = WesnothPromptBuilder()
        self._init_providers()

    def _init_providers(self) -> None:
        oai_key = os.getenv("OPENAI_API_KEY", "")
        ds_key  = os.getenv("DEEPSEEK_API_KEY", "")

        if len(oai_key) > 10:
            from ai.openai_provider import OpenAIProvider
            self.prov_1 = OpenAIProvider(agent_id="AI_A", api_key=oai_key, temperature=0.7)
            print("[+] OpenAI GPT-4o aktif (Temp=0.7)")
        else:
            from ai.baseline_agents import GreedyProvider
            self.prov_1 = GreedyProvider(agent_id="AI_A")
            print("[-] OPENAI_API_KEY yok")

        if len(ds_key) > 10:
            from ai.deepseek_provider import DeepSeekProvider
            self.prov_2 = DeepSeekProvider(agent_id="AI_B", api_key=ds_key, temperature=0.7)
            print("[+] DeepSeek aktif (Temp=0.7)")
        else:
            from ai.baseline_agents import DefensiveProvider
            self.prov_2 = DefensiveProvider(agent_id="AI_B")
            print("[-] DEEPSEEK_API_KEY yok")

    def _build_side_state(self, side: int, turn: int) -> dict:
        my_side = _GAME_STATE["sides"][str(side)]
        other_side = 2 if side == 1 else 1
        other_data = _GAME_STATE["sides"][str(other_side)]

        island_bonus = 15 if _GAME_STATE["island_controller"] == my_side["name"] else 0
        total_income = 8 + (my_side["farms"] * 3) + (my_side["mines"] * 5) + island_bonus

        dip_str = f"{_GAME_STATE['pact_type']} (Kalan: {_GAME_STATE['pact_turns_remaining']} tur)" if _GAME_STATE["pact_turns_remaining"] > 0 else "Tarafsiz / Pakt Yok"
        inbox = _GAME_STATE["last_letter_for_1"] if side == 1 else _GAME_STATE["last_letter_for_2"]

        return {
            "turn": turn,
            "side": side,
            "side_name": my_side["name"],
            "gold": my_side["gold"],
            "income": total_income,
            "villages": my_side["villages"] + my_side["farms"],
            "farms": my_side["farms"],
            "mines": my_side["mines"],
            "forts": my_side["forts"],
            "ports": my_side["ports"],
            "ships": my_side["ships"],
            "island_controller": _GAME_STATE["island_controller"],
            "diplomatic_status": dip_str,
            "incoming_letter": inbox,
            "my_units": [{"id": f"u_{i}", "type": "Unit"} for i in range(my_side["units"])],
            "enemy_units": [{"id": f"eu_{j}", "type": "Enemy"} for j in range(other_data["units"])],
        }

    async def generate_side_orders(self, side: int, turn: int) -> dict:
        _GAME_STATE["turn"] = turn
        side_name = _GAME_STATE["sides"][str(side)]["name"]

        provider = self.prov_1 if side == 1 else self.prov_2
        agent_id = "AI_A" if side == 1 else "AI_B"
        model_name = getattr(provider, "model_name", "AI")

        state = self._build_side_state(side, turn)
        system_prompt = self.pb.system_prompt(state)
        user_prompt   = self.pb.user_prompt(state)

        start_time = time.perf_counter()
        try:
            raw_response = await provider.decide_async(system_prompt, user_prompt)
        except Exception as e:
            raw_response = json.dumps({
                "thought": f"Taarruz emri verildi!",
                "diplomacy": None,
                "actions": [{"type": "RECRUIT", "unit": "HEAVY"}, {"type": "ORDER_ARMY", "stance": "CONQUER_ISLAND"}]
            })
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        thought = f"{side_name} stratejik hamlelerini uyguluyor."
        dip_obj = None
        actions_list = []
        try:
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            data = json.loads(cleaned)
            thought = data.get("thought", thought)
            dip_obj = data.get("diplomacy", None)
            actions_list = data.get("actions", [])
        except Exception as e:
            print(f"JSON Parse Hatasi ({side_name}): {e}")
            actions_list = [{"type": "RECRUIT", "unit": "INFANTRY"}, {"type": "ORDER_ARMY", "stance": "CONQUER_ISLAND"}]

        # Process Diplomacy
        dip_msg = None
        proposal = None
        if dip_obj and isinstance(dip_obj, dict):
            dip_msg = dip_obj.get("message", None)
            proposal = dip_obj.get("proposal", None)
            if dip_msg:
                other_key = "last_letter_for_2" if side == 1 else "last_letter_for_1"
                _GAME_STATE[other_key] = f"[{side_name}]: {dip_msg}"
                _DIPLOMACY_LOG.append({
                    "turn": turn,
                    "from": side_name,
                    "proposal": proposal,
                    "message": dip_msg,
                    "timestamp": time.strftime("%H:%M:%S")
                })
            if proposal in ["OFFER_NON_AGGRESSION", "OFFER_ALLIANCE"]:
                _GAME_STATE["pact_type"] = "Saldırmazlık Paktı"
                _GAME_STATE["pact_turns_remaining"] = 3
            elif proposal == "ACCEPT_PROPOSAL":
                _GAME_STATE["pact_type"] = "İttifak Onaylandı"
                _GAME_STATE["pact_turns_remaining"] = 3
            elif proposal == "DECLARE_WAR":
                _GAME_STATE["pact_type"] = "SAVAŞ İLANI"
                _GAME_STATE["pact_turns_remaining"] = 0

        # Process Actions & Building Effects
        for act in actions_list:
            act_type = act.get("type", "")
            if act_type == "BUILD":
                b_type = act.get("building", "FARM")
                if b_type == "FARM":
                    _GAME_STATE["sides"][str(side)]["farms"] += 1
                    _GAME_STATE["sides"][str(side)]["gold"] = max(10, _GAME_STATE["sides"][str(side)]["gold"] - 25)
                elif b_type == "FORT":
                    _GAME_STATE["sides"][str(side)]["forts"] += 1
                    _GAME_STATE["sides"][str(side)]["gold"] = max(10, _GAME_STATE["sides"][str(side)]["gold"] - 40)
                elif b_type == "MINE":
                    _GAME_STATE["sides"][str(side)]["mines"] += 1
                    _GAME_STATE["sides"][str(side)]["gold"] = max(10, _GAME_STATE["sides"][str(side)]["gold"] - 35)
                elif b_type == "PORT":
                    _GAME_STATE["sides"][str(side)]["ports"] += 1
                    _GAME_STATE["sides"][str(side)]["gold"] = max(10, _GAME_STATE["sides"][str(side)]["gold"] - 50)
            elif act_type == "RECRUIT":
                u_req = act.get("unit", "INFANTRY")
                if u_req == "SHIP":
                    _GAME_STATE["sides"][str(side)]["ships"] += 1
                    _GAME_STATE["sides"][str(side)]["gold"] = max(10, _GAME_STATE["sides"][str(side)]["gold"] - 30)
                else:
                    _GAME_STATE["sides"][str(side)]["units"] = min(18, _GAME_STATE["sides"][str(side)]["units"] + 1)
                    _GAME_STATE["sides"][str(side)]["gold"] = max(20, _GAME_STATE["sides"][str(side)]["gold"] - 16)
            elif act_type == "ORDER_ARMY":
                stance = act.get("stance", "")
                if stance == "CONQUER_ISLAND" and turn >= 3:
                    _GAME_STATE["island_controller"] = side_name

        # Add income to gold for next turn
        _GAME_STATE["sides"][str(side)]["gold"] += state["income"]

        # Telemetry
        _TELEMETRY.append({
            "turn": turn,
            "agent_id": agent_id,
            "agent_name": side_name,
            "model": model_name,
            "latency_ms": round(latency_ms, 1),
            "thought": thought,
            "diplomatic_proposal": proposal,
            "diplomatic_message": dip_msg,
            "actions": actions_list,
            "timestamp": time.strftime("%H:%M:%S"),
        })
        if len(_TELEMETRY) > 300:
            _TELEMETRY.pop(0)

        print(f"[{time.strftime('%H:%M:%S')}] TUR {turn} | {side_name} ({model_name})")
        print(f"  Dusunce : {thought[:110]}")
        if dip_msg:
            print(f"  Mektup  : [{proposal}] {dip_msg[:90]}")
        print(f"  Hamleler: {actions_list}")
        print(f"  Gecikme : {latency_ms:.0f}ms\n")

        return {
            "turn": turn,
            "side": side,
            "thought": thought,
            "diplomatic_message": dip_msg,
            "proposal": proposal,
            "actions": actions_list,
        }

    async def run_loop(self) -> None:
        print("\n" + "=" * 65)
        print(">>> Grand Strategy WorldBox Arena Aktif! <<<")
        print("    Web Inspector: http://localhost:8000")
        print("=" * 65 + "\n")

        turn = 1
        while True:
            if _GAME_STATE["pact_turns_remaining"] > 0:
                _GAME_STATE["pact_turns_remaining"] -= 1

            for side in [1, 2]:
                orders = await self.generate_side_orders(side, turn)
                orders_file = SCENARIOS_DIR / f"orders_side_{side}.json"
                orders_file.write_text(json.dumps(orders, ensure_ascii=False), encoding="utf-8")
                await asyncio.sleep(3.2)
            turn += 1
            await asyncio.sleep(2.0)


def main() -> None:
    start_web_inspector(port=8000)
    server = WesnothBridgeServer()
    asyncio.run(server.run_loop())


if __name__ == "__main__":
    main()
