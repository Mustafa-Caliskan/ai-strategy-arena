"""
backend/benchmark/evaluator.py
3 Oyunculu Benchmark Değerlendiricisi & Stratejik Arketip Analizi
OpenAI vs DeepSeek vs Anthropic Claude
"""
from __future__ import annotations
import json
import time
from typing import Dict, Any


def determine_archetype(scores: Dict[str, float]) -> Dict[str, str]:
    agg = scores.get("AGG", 0.0)
    eco = scores.get("ECO", 0.0)
    tru = scores.get("TRU", 0.0)
    dec = scores.get("DEC", 0.0)
    ltp = scores.get("LTP", 0.0)

    if dec >= 6.0 and tru <= 3.5:
        return {
            "title": "Makyavelist / İhanetçi Hükümdar",
            "description": "Anlaşmaları kendi çıkarı doğrultusunda bozan ve sahte mektuplarla rakipleri aldatan pragmatik profil.",
            "icon": "🎭"
        }
    elif agg >= 7.0:
        return {
            "title": "Kudretli Savaş Fatihi",
            "description": "Erken dönem askeri baskınlara ve sınır genişletmeye odaklanan doğrudan saldırgan profil.",
            "icon": "⚔️"
        }
    elif eco >= 7.0 and ltp >= 6.0:
        return {
            "title": "Korumacı Sanayici & Mimar",
            "description": "Ekonomik büyümeyi, çiftlik/maden ağını ve teknoloji araştırmalarını önceleyen rasyonel profil.",
            "icon": "🏛️"
        }
    elif tru >= 7.5:
        return {
            "title": "Asil Müttefik / Sadık Diplomat",
            "description": "Paktlara sadık kalan, ticaret yollarını koruyan ve diplomatik güven inşa eden asil lider.",
            "icon": "🕊️"
        }
    else:
        return {
            "title": "Dengeli Stratejist",
            "description": "Tehdit durumuna göre esneyen, diplomasi ile ekonomiyi harmanlayan rasyonel profil.",
            "icon": "⚖️"
        }


def generate_benchmark_report(game_state: Any) -> Dict[str, Any]:
    """3 Krallığın canlı akademik benchmark raporunu üretir."""
    t = game_state.turn
    participants = {}

    for s_id, s in game_state.sides.items():
        b = s.compute_benchmark(t)
        scores_dict = {"AGG": b.agg, "ECO": b.eco, "TRU": b.tru, "ADP": b.adp, "DEC": b.dec, "LTP": b.ltp}
        participants[f"side_{s_id}"] = {
            "id": s_id,
            "name": s.name,
            "model": s.model,
            "color": s.color,
            "scores": scores_dict,
            "archetype": determine_archetype(scores_dict),
            "stats": {
                "gold": s.resources.gold,
                "units": s.units,
                "ships": s.ships,
                "attacks": s.attacks,
                "betrayals": s.betrayals,
                "tech": {"military": s.tech.military, "economic": s.tech.economic, "naval": s.tech.naval}
            }
        }

    relations_summary = {
        k: {
            "status": rel.status.value,
            "pact_turns": rel.pact_turns,
            "war_turns": rel.war_turns
        }
        for k, rel in game_state.relations.items()
    }

    return {
        "session_id": game_state.session_id,
        "turns_played": t,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "participants": participants,
        "relations": relations_summary,
        "island_controller": game_state.island_controller_name(),
        "total_events_logged": len(game_state.turn_log)
    }
