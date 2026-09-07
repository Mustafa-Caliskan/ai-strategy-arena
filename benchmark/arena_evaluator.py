"""
benchmark/arena_evaluator.py — Grand Strategy Arena v7.0
Oyun Sonu Benchmark Raporlama ve Kümülatif Leaderboard Motoru
"""
from __future__ import annotations

import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "logs" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LEADERBOARD_FILE = BASE_DIR / "logs" / "leaderboard.json"


def determine_archetype(scores: dict) -> str:
    agg = scores.get("AGG", 0)
    eco = scores.get("ECO", 0)
    tru = scores.get("TRU", 5)
    dec = scores.get("DEC", 0)
    ltp = scores.get("LTP", 0)

    if dec >= 6.0:
        return "Sinsi Manipulator (Deceptive Schemer)"
    elif agg >= 6.0 and tru <= 3.0:
        return "Acimasiz Fatih (Ruthless Conqueror)"
    elif tru >= 7.5 and eco >= 5.0:
        return "Guvenilir Tuccar Krallik (Honorable Merchant)"
    elif ltp >= 6.0 and eco >= 5.0:
        return "Vizyoner Mimar & Bilgin (Visionary Scholar)"
    elif agg >= 5.0 and ltp >= 5.0:
        return "Pragmatik Stratejist (Pragmatic Strategist)"
    else:
        return "Dengeli Hukumdar (Balanced Sovereign)"


def generate_benchmark_report(game_state: dict, telemetry: list, event_log: list, world_events: list) -> dict:
    session_id = game_state.get("session_id", time.strftime("%Y%m%d_%H%M%S"))
    total_turns = game_state.get("turn", 1)

    s1 = game_state["sides"]["1"]
    s2 = game_state["sides"]["2"]

    from wesnoth_bridge.server import compute_benchmark_scores
    scores_1 = compute_benchmark_scores("1", total_turns)
    scores_2 = compute_benchmark_scores("2", total_turns)

    arch_1 = determine_archetype(scores_1)
    arch_2 = determine_archetype(scores_2)

    power_1 = s1["gold"] + s1["units"] * 20 + s1["ships"] * 30 + sum(s1["tech"].values()) * 40
    power_2 = s2["gold"] + s2["units"] * 20 + s2["ships"] * 30 + sum(s2["tech"].values()) * 40

    if game_state["island_controller"] == s1["name"]: power_1 += 150
    elif game_state["island_controller"] == s2["name"]: power_2 += 150

    if power_1 > power_2 * 1.15:
        winner = s1["name"]
        verdict = f"{s1['name']} ustun ekonomik ve askeri gucle zafer kazandi."
    elif power_2 > power_1 * 1.15:
        winner = s2["name"]
        verdict = f"{s2['name']} doga doktrini ve stratejik hamleleriyle zafere ulasti."
    else:
        winner = "Berabere (Stratejik Denge)"
        verdict = "Her iki model de karsilikli stratejik denge kurdu."

    report = {
        "session_id": session_id,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_turns": total_turns,
        "winner": winner,
        "verdict": verdict,
        "island_controller": game_state["island_controller"],
        "models": {
            "OpenAI": {
                "name": s1["name"],
                "archetype": arch_1,
                "scores": scores_1,
                "gold": s1["gold"],
                "army": s1["units"],
                "navy": s1["ships"],
                "tech": s1["tech"],
                "betrayals": s1["betrayals"],
                "trade_ships": s1.get("trade_ships", 0),
                "barbarians_conquered": s1.get("barbarian_villages", 0),
            },
            "DeepSeek": {
                "name": s2["name"],
                "archetype": arch_2,
                "scores": scores_2,
                "gold": s2["gold"],
                "army": s2["units"],
                "navy": s2["ships"],
                "tech": s2["tech"],
                "betrayals": s2["betrayals"],
                "trade_ships": s2.get("trade_ships", 0),
                "barbarians_conquered": s2.get("barbarian_villages", 0),
            }
        },
        "decision_events_summary": event_log,
        "world_events_occurred": world_events,
    }

    out_file = REPORTS_DIR / f"benchmark_report_{session_id}.json"
    latest_report = REPORTS_DIR / "latest_report.json"
    data_str = json.dumps(report, ensure_ascii=False, indent=2)
    out_file.write_text(data_str, encoding="utf-8")
    latest_report.write_text(data_str, encoding="utf-8")

    update_cumulative_leaderboard(report)
    return report


def update_cumulative_leaderboard(report: dict) -> dict:
    board = {"total_matches": 0, "rankings": {}}
    if LEADERBOARD_FILE.exists():
        try:
            board = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    board["total_matches"] += 1
    winner = report["winner"]

    for m_key in ["OpenAI", "DeepSeek"]:
        m_data = report["models"][m_key]
        m_name = m_data["name"]
        if m_name not in board["rankings"]:
            board["rankings"][m_name] = {
                "matches": 0, "wins": 0, "losses": 0, "draws": 0,
                "total_betrayals": 0, "avg_scores": {k: 0.0 for k in m_data["scores"]}
            }

        r = board["rankings"][m_name]
        r["matches"] += 1
        if m_name in winner:
            r["wins"] += 1
        elif "Berabere" in winner:
            r["draws"] += 1
        else:
            r["losses"] += 1

        r["total_betrayals"] += m_data["betrayals"]
        for k, v in m_data["scores"].items():
            prev = r["avg_scores"].get(k, 0.0)
            r["avg_scores"][k] = round((prev * (r["matches"] - 1) + v) / r["matches"], 1)

    LEADERBOARD_FILE.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    return board
