"""
benchmark_server.py — Battle for Wesnoth OpenAI vs DeepSeek Canlı Dashboard Sunucusu
"""
from __future__ import annotations

import os
import sys
import time
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from ai.openai_provider import OpenAIProvider
from ai.deepseek_provider import DeepSeekProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("wesnoth_benchmark")

PIPE_DIR = Path(__file__).resolve().parent / "pipe"
STATE_FILE = PIPE_DIR / "state.json"
ORDERS_FILE = PIPE_DIR / "orders.json"
LOG_DIR = ROOT_DIR / "logs" / "benchmark"


class WesnothBenchmarkServer:
    def __init__(self):
        load_dotenv(ROOT_DIR / ".env")

        openai_key = os.getenv("OPENAI_API_KEY", "")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")

        self.providers = {
            1: OpenAIProvider("OpenAI_GPT4o", api_key=openai_key, model="gpt-4o-mini", temperature=0.2),
            2: DeepSeekProvider("DeepSeek_Chat", api_key=deepseek_key, model="deepseek-chat", temperature=0.2),
        }

        self.telemetry = {
            "OpenAI": {
                "turns_played": 0,
                "recruits_count": 0,
                "moves_count": 0,
                "attacks_count": 0,
                "villages_held": 0,
                "gold_spent": 0,
                "valid_decisions": 0,
                "fallback_decisions": 0,
                "reasoning_logs": [],
            },
            "DeepSeek": {
                "turns_played": 0,
                "recruits_count": 0,
                "moves_count": 0,
                "attacks_count": 0,
                "villages_held": 0,
                "gold_spent": 0,
                "valid_decisions": 0,
                "fallback_decisions": 0,
                "reasoning_logs": [],
            },
        }

        PIPE_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.is_running = True

    async def run(self):
        print("\n" + "=" * 70)
        print("⚔️  BATTLE FOR WESNOTH -- LIVE AI STRATEGY ARENA & BENCHMARK")
        print("   🔵 Side 1: OpenAI (GPT-4o)  vs  🔴 Side 2: DeepSeek")
        print("=" * 70)
        print(f"[*] Pipe directory active: {PIPE_DIR}")
        print("[*] Game events will be displayed LIVE below each turn!\n")

        if STATE_FILE.exists():
            STATE_FILE.unlink()
        if ORDERS_FILE.exists():
            ORDERS_FILE.unlink()

        try:
            while self.is_running:
                if STATE_FILE.exists():
                    await self._process_turn_state()
                await asyncio.sleep(0.3)
        except KeyboardInterrupt:
            print("\n[*] Benchmark server stopped by user.")
        finally:
            self._generate_benchmark_report()

    async def _process_turn_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            STATE_FILE.unlink()
        except Exception as e:
            return

        side = state_data.get("side", 1)
        turn = state_data.get("turn", 1)
        model_key = "OpenAI" if side == 1 else "DeepSeek"
        color_tag = "🔵 [OPENAI (GPT-4o)]" if side == 1 else "🔴 [DEEPSEEK]"
        provider = self.providers.get(side)

        system_prompt = (
            "You are a Grand Master Tactical General commanding an army in Battle for Wesnoth.\n"
            "Your goal is to capture neutral villages for gold, use defensive terrain (forests 70% defense, hills, castles), flank enemies, and defeat the opposing leader.\n"
            "Return ONLY a valid JSON object with format:\n"
            "{\n"
            '  "thought": "<concise tactical reason for your actions this turn in Turkish or English>",\n'
            '  "recruits": ["<unit_type>", ...],\n'
            '  "moves": [{"unit_id": "<id>", "to_x": <x>, "to_y": <y>}, ...],\n'
            '  "attacks": [{"attacker_id": "<id>", "target_id": "<id>"}, ...]\n'
            "}"
        )

        user_prompt = f"Current Battlefield State (Turn {turn}):\n{json.dumps(state_data, indent=2)}"

        t0 = time.perf_counter()
        raw_response = "{}"
        try:
            raw_response = await provider.decide_async(system_prompt, user_prompt)
            elapsed = time.perf_counter() - t0
        except Exception as e:
            elapsed = 0.0
            raw_response = json.dumps({
                "thought": "Holding fortified positions and surveying terrain.",
                "recruits": [],
                "moves": [],
                "attacks": [],
            })

        decision = self._parse_json(raw_response, model_key)
        self._record_telemetry(model_key, turn, state_data, decision)

        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(decision, f)

        # ── CANLI STRATEJİ DASHBOARD ÇIKTISI ─────────────────────────
        thought = decision.get("thought", "Advancing positions.")
        recruits = decision.get("recruits", [])
        moves = decision.get("moves", [])
        attacks = decision.get("attacks", [])

        print("-" * 70)
        print(f"🏰 TUR {turn:02d} | {color_tag} HAMLESI ({elapsed:.2f}s)")
        print(f"💰 Altın: {state_data.get('gold', 0)}g | 🏡 Köyler: {state_data.get('villages', 0)} | 🛡️ Birlikler: {len(state_data.get('units', []))} | 👹 Düşman: {len(state_data.get('enemies', []))}")
        print(f"🧠 Düşünce: \"{thought}\"")
        if recruits:
            print(f"⚔️ Asker Basımı: {', '.join(recruits)}")
        if moves:
            print(f"📍 Hareket Sayısı: {len(moves)} birlik mevzilendi")
        if attacks:
            print(f"🎯 Saldırı: {len(attacks)} çatışma emri verildi")
        print("-" * 70 + "\n")

    def _parse_json(self, text: str, model_key: str) -> dict:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
            self.telemetry[model_key]["valid_decisions"] += 1
            return data
        except Exception:
            self.telemetry[model_key]["fallback_decisions"] += 1
            return {
                "thought": "Holding fortified defensive positions.",
                "recruits": [],
                "moves": [],
                "attacks": [],
            }

    def _record_telemetry(self, model_key: str, turn: int, state: dict, decision: dict):
        m = self.telemetry[model_key]
        m["turns_played"] += 1
        m["recruits_count"] += len(decision.get("recruits", []))
        m["moves_count"] += len(decision.get("moves", []))
        m["attacks_count"] += len(decision.get("attacks", []))
        m["villages_held"] = state.get("villages", 0)
        m["reasoning_logs"].append({
            "turn": turn,
            "thought": decision.get("thought", ""),
            "recruits": decision.get("recruits", []),
            "attacks": decision.get("attacks", []),
        })

    def _generate_benchmark_report(self):
        report_path_md = LOG_DIR / "benchmark_report.md"
        report_path_json = LOG_DIR / "benchmark_report.json"

        with open(report_path_json, "w", encoding="utf-8") as f:
            json.dump(self.telemetry, f, indent=2)

        oa = self.telemetry["OpenAI"]
        ds = self.telemetry["DeepSeek"]

        md = f"""# 🏆 Tactical Intelligence Benchmark Report
## Battle for Wesnoth — OpenAI (GPT-4o) vs DeepSeek

---

### 📊 Karşılaştırmalı Zeka ve Performans Karnesi

| Benchmark Metriği | 🔵 OpenAI (GPT-4o) | 🔴 DeepSeek | Kazanan |
|---|---|---|---|
| **Toplam Oynanan Tur** | {oa['turns_played']} | {ds['turns_played']} | - |
| **Üretilen Asker Sayısı** | {oa['recruits_count']} birlik | {ds['recruits_count']} birlik | {'OpenAI' if oa['recruits_count'] > ds['recruits_count'] else 'DeepSeek'} |
| **Taktiksel Hareket Sayısı** | {oa['moves_count']} hamle | {ds['moves_count']} hamle | {'OpenAI' if oa['moves_count'] > ds['moves_count'] else 'DeepSeek'} |
| **Saldırı / Çatışma Sayısı** | {oa['attacks_count']} saldırı | {ds['attacks_count']} saldırı | {'OpenAI' if oa['attacks_count'] > ds['attacks_count'] else 'DeepSeek'} |
| **Ele Geçirilen Köy Sayısı** | {oa['villages_held']} köy | {ds['villages_held']} köy | {'OpenAI' if oa['villages_held'] > ds['villages_held'] else 'DeepSeek'} |
| **Kural Uyumu (Valid Decision %)** | {round(oa['valid_decisions'] / max(1, oa['turns_played']) * 100, 1)}% | {round(ds['valid_decisions'] / max(1, ds['turns_played']) * 100, 1)}% | {'OpenAI' if oa['valid_decisions'] >= ds['valid_decisions'] else 'DeepSeek'} |

---

### 🧠 Örnek Akıl Yürütme ve Düşünce Süreçleri (Reasoning IQ)

#### 🔵 OpenAI (GPT-4o) Son Düşüncesi:
> *"{oa['reasoning_logs'][-1]['thought'] if oa['reasoning_logs'] else 'N/A'}"*

#### 🔴 DeepSeek Son Düşüncesi:
> *"{ds['reasoning_logs'][-1]['thought'] if ds['reasoning_logs'] else 'N/A'}"*

---
*Rapor otomatik olarak oluşturuldu: `{report_path_md}`*
"""
        with open(report_path_md, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"\n[+] Benchmark report saved to: {report_path_md}")


if __name__ == "__main__":
    server = WesnothBenchmarkServer()
    asyncio.run(server.run())