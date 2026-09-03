"""
server.py — AI Strategy Arena Canli Web Telemetri ve 6D Benchmark Inspector Sunucusu
"""
from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from simulation.turn_manager import TurnManager

_GLOBAL_MANAGER: Optional["TurnManager"] = None


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ AI Strategy Arena — 6D Benchmark & Telemetri Inspector</title>
    <style>
        :root {
            --bg-dark: #0b0d14;
            --bg-card: #151824;
            --bg-card-hover: #1f2333;
            --border-color: #262b3d;
            --text-main: #e6ebf5;
            --text-muted: #8892b0;
            --accent-openai: #3b82f6;
            --accent-deepseek: #ef4444;
            --accent-gold: #f59e0b;
            --accent-green: #10b981;
            --accent-purple: #8b5cf6;
            --accent-red: #dc2626;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            padding: 20px 24px;
            font-size: 13px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }
        .header h1 { font-size: 22px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .badge-live {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .live-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

        /* Top Bar Info */
        .top-info-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .info-pill {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .info-pill-title { font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
        .info-pill-value { font-size: 14px; font-weight: 700; color: var(--text-main); }

        /* Country / Faction Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            position: relative;
            overflow: hidden;
        }
        .stat-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
        }
        .stat-card.openai::before { background: var(--accent-openai); }
        .stat-card.deepseek::before { background: var(--accent-deepseek); }

        .stat-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
        }
        .stat-card-title { font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
        .betrayal-badge {
            background: rgba(220, 38, 38, 0.2);
            color: #f87171;
            border: 1px solid #ef4444;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
        }

        /* Resource Grid inside Card */
        .res-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            background: rgba(0, 0, 0, 0.25);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 14px;
            text-align: center;
        }
        .res-item { display: flex; flex-direction: column; gap: 2px; }
        .res-label { font-size: 10px; color: var(--text-muted); }
        .res-val { font-size: 13px; font-weight: 700; }

        /* 6D Benchmark Bar */
        .bench-section {
            margin-top: 10px;
            border-top: 1px solid var(--border-color);
            padding-top: 12px;
        }
        .bench-title { font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700; margin-bottom: 8px; }
        .bench-bars { display: flex; flex-direction: column; gap: 6px; }
        .bench-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 11px; }
        .bench-label { width: 110px; color: var(--text-muted); }
        .bench-bar-bg { flex: 1; height: 7px; background: #222638; border-radius: 4px; overflow: hidden; }
        .bench-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
        .bench-num { width: 32px; text-align: right; font-weight: 700; }

        /* Section Titles */
        .section-title {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 12px;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Event Log Cards */
        .event-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }
        .event-card {
            background: var(--bg-card);
            border: 1px solid #3b4252;
            border-left: 4px solid var(--accent-gold);
            border-radius: 8px;
            padding: 12px 14px;
        }
        .event-header { display: flex; justify-content: space-between; font-weight: 700; font-size: 12px; margin-bottom: 4px; }
        .event-choice-tag {
            background: rgba(245, 158, 11, 0.2);
            color: var(--accent-gold);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
        }
        .event-desc { font-size: 11px; color: var(--text-muted); }

        /* Telemetry Table */
        .table-container {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow-x: auto;
        }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th, td { padding: 10px 14px; border-bottom: 1px solid var(--border-color); }
        th { background: #1a1e2d; font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700; }
        tr:hover { background: var(--bg-card-hover); }

        .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
        .tag-openai { background: rgba(59, 130, 246, 0.2); color: var(--accent-openai); }
        .tag-deepseek { background: rgba(239, 68, 68, 0.2); color: var(--accent-deepseek); }
        .tag-betray { background: #dc2626; color: #fff; font-weight: bold; animation: pulse 1s infinite; }

        .btn-inspect {
            background: #252a3d;
            border: 1px solid #3b425a;
            color: var(--text-main);
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.2s;
        }
        .btn-inspect:hover { background: #3b425a; }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(4px);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            width: 800px;
            max-width: 90vw;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-body { padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
        .code-box {
            background: #090a10;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            font-family: monospace;
            font-size: 11px;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
            color: #cbd5e1;
        }
        .btn-close { background: none; border: none; font-size: 20px; color: var(--text-muted); cursor: pointer; }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ AI Strategy Arena — 6D Benchmark & Canlı Telemetri</h1>
        <div class="badge-live"><div class="live-dot"></div> CANLI YAYIN (1s)</div>
    </div>

    <!-- Top State Overview -->
    <div class="top-info-bar">
        <div class="info-pill">
            <span class="info-pill-title">Mevcut Tur</span>
            <span class="info-pill-value" id="topTurn">Tur 1</span>
        </div>
        <div class="info-pill">
            <span class="info-pill-title">Diplomasi Durumu</span>
            <span class="info-pill-value" id="topDiplomacy" style="color:var(--accent-gold);">Pakt Yok</span>
        </div>
        <div class="info-pill">
            <span class="info-pill-title">Merkez Hazine Adası</span>
            <span class="info-pill-value" id="topIsland" style="color:var(--accent-green);">Tarafsız</span>
        </div>
        <div class="info-pill">
            <span class="info-pill-title">Aktif Olay Kartı</span>
            <span class="info-pill-value" id="topEvent" style="color:var(--accent-purple);">-</span>
        </div>
    </div>

    <!-- Country Cards with 6D Benchmark -->
    <div class="stats-grid" id="statsGrid"></div>

    <!-- Event Decision Log -->
    <div id="eventLogContainer" style="display:none;">
        <div class="section-title">🎴 Olay Kartı Karar Geçmişi (Decision Events)</div>
        <div class="event-grid" id="eventGrid"></div>
    </div>

    <!-- Live Telemetry Stream -->
    <div class="section-title">🔍 Gerçek Zamanlı LLM Çağrıları & 6D Benchmark Kayıtları</div>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Tur</th>
                    <th>Model / Taraf</th>
                    <th>Eylemler</th>
                    <th>Gecikme</th>
                    <th>Stratejik Düşünce (Thought)</th>
                    <th>Diplomasi / Mektup</th>
                    <th>Olay Seçimi</th>
                    <th>Detay</th>
                </tr>
            </thead>
            <tbody id="telemetryTable">
                <tr><td colspan="8" style="text-align:center; color:#8c96ac;">Veriler bekleniyor...</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Modal -->
    <div class="modal" id="inspectModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">API Çağrı Detayları</h3>
                <button class="btn-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div>
                    <div style="font-weight:700; color:var(--text-muted); margin-bottom:4px;">📜 STRATEJİK DÜŞÜNCE:</div>
                    <div class="code-box" id="modalThought" style="color:#93c5fd;"></div>
                </div>
                <div>
                    <div style="font-weight:700; color:var(--text-muted); margin-bottom:4px;">⚔️ 6D BENCHMARK SKORU:</div>
                    <div class="code-box" id="modalBench" style="color:#fcd34d;"></div>
                </div>
                <div>
                    <div style="font-weight:700; color:var(--text-muted); margin-bottom:4px;">📦 PLANLANAN ÇOKLU EYLEMLER:</div>
                    <div class="code-box" id="modalActions" style="color:#34d399;"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let telemetryData = [];

        const BENCH_COLORS = {
            AGG: "#ef4444",
            ECO: "#10b981",
            TRU: "#3b82f6",
            ADP: "#8b5cf6",
            DEC: "#f97316",
            LTP: "#06b6d4"
        };
        const BENCH_NAMES = {
            AGG: "Agresiflik (AGG)",
            ECO: "Ekonomi (ECO)",
            TRU: "Güvenilirlik (TRU)",
            ADP: "Uyumluluk (ADP)",
            DEC: "Aldatma (DEC)",
            LTP: "Uzun Vade (LTP)"
        };

        async function fetchStatus() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();
                renderTopInfo(data);
                renderStats(data);
                renderEventLog(data.event_log || []);
                renderTelemetry(data.telemetry || []);
            } catch (e) {
                console.error(e);
            }
        }

        function renderTopInfo(data) {
            document.getElementById("topTurn").innerText = `Tur ${data.turn || 1}`;
            document.getElementById("topDiplomacy").innerText = data.diplomacy_status || "Tarafsız";
            document.getElementById("topIsland").innerText = data.island_controller || "Tarafsız";
            document.getElementById("topEvent").innerText = data.current_event || "Yok";
        }

        function renderStats(data) {
            const grid = document.getElementById("statsGrid");
            if (!data.countries) return;

            let html = "";
            data.countries.forEach(c => {
                const isOAI = c.agent_id === "AI_A";
                const cardClass = isOAI ? "openai" : "deepseek";
                const crest = isOAI ? "🔵" : "🔴";
                const r = c.resources || {};
                const b = c.benchmark || {};

                const betrayalHtml = r.betrayals > 0 
                    ? `<span class="betrayal-badge">⚠️ ${r.betrayals} İHANET</span>` 
                    : "";

                let benchHtml = "";
                for (const [k, name] of Object.entries(BENCH_NAMES)) {
                    const val = b[k] !== undefined ? b[k] : 0;
                    const pct = Math.min(100, Math.round(val * 10));
                    const col = BENCH_COLORS[k] || "#fff";
                    benchHtml += `
                    <div class="bench-row">
                        <span class="bench-label">${name}</span>
                        <div class="bench-bar-bg">
                            <div class="bench-bar-fill" style="width:${pct}%; background:${col};"></div>
                        </div>
                        <span class="bench-num" style="color:${col};">${val.toFixed(1)}</span>
                    </div>`;
                }

                html += `
                <div class="stat-card ${cardClass}">
                    <div class="stat-card-header">
                        <div class="stat-card-title">${crest} ${c.name}</div>
                        ${betrayalHtml}
                    </div>
                    <div class="res-grid">
                        <div class="res-item"><span class="res-label">Altın</span><span class="res-val" style="color:var(--accent-gold);">${r.gold || 0} 💰</span></div>
                        <div class="res-item"><span class="res-label">Ordu</span><span class="res-val">${r.army || 0} ⚔️</span></div>
                        <div class="res-item"><span class="res-label">Donanma</span><span class="res-val" style="color:var(--accent-openai);">${r.navy || 0} ⚓</span></div>
                        <div class="res-item"><span class="res-label">Köyler</span><span class="res-val">${r.territory || 0} 🌾</span></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-bottom:8px;">
                        <span>Çiftlik: ${r.farms || 0} | Maden: ${r.mines || 0}</span>
                        <span>Kale: ${r.forts || 0} | Tersane: ${r.ports || 0}</span>
                    </div>
                    <div class="bench-section">
                        <div class="bench-title">6-Boyutlu Strateji Profili</div>
                        <div class="bench-bars">${benchHtml}</div>
                    </div>
                </div>`;
            });
            grid.innerHTML = html;
        }

        function renderEventLog(events) {
            const container = document.getElementById("eventLogContainer");
            const grid = document.getElementById("eventGrid");
            if (!events || events.length === 0) {
                container.style.display = "none";
                return;
            }
            container.style.display = "block";
            let html = "";
            events.slice(-6).reverse().forEach(ev => {
                html += `
                <div class="event-card">
                    <div class="event-header">
                        <span>T${ev.turn} — ${ev.title}</span>
                        <span class="event-choice-tag">Seçenek ${ev.choice}</span>
                    </div>
                    <div class="event-desc">${ev.side}: <em>${ev.label}</em></div>
                </div>`;
            });
            grid.innerHTML = html;
        }

        function renderTelemetry(list) {
            telemetryData = list;
            const tbody = document.getElementById("telemetryTable");
            if (!list || list.length === 0) return;

            let rows = "";
            [...list].reverse().forEach((item, idx) => {
                const originalIndex = list.length - 1 - idx;
                const isOAI = item.agent_id === "AI_A";
                const tagClass = isOAI ? "tag-openai" : "tag-deepseek";

                const isBetrayal = item.diplomatic_proposal === "BETRAY_ATTACK";
                const dipBadge = isBetrayal
                    ? `<span class="tag tag-betray">⚠️ İHANET!</span>`
                    : (item.diplomatic_proposal ? `<code style="color:var(--accent-gold); font-size:11px;">[${item.diplomatic_proposal}]</code>` : '-');

                const actionsSummary = (item.actions || []).map(a => `${a.type || '?'}:${a.building || a.unit || a.stance || ''}`).join(', ');

                const evChoiceBadge = item.event_choice 
                    ? `<span style="background:#78350f; color:#fde68a; padding:2px 6px; border-radius:4px; font-weight:bold;">Seçim ${item.event_choice}</span>` 
                    : '-';

                rows += `
                <tr>
                    <td><strong>T${item.turn}</strong></td>
                    <td><span class="tag ${tagClass}">${item.agent_name}</span></td>
                    <td style="max-width:180px; font-size:11px; color:#cbd5e1;">${actionsSummary || '-'}</td>
                    <td><span style="color:#10b981; font-weight:600;">${item.latency_ms} ms</span></td>
                    <td style="max-width:260px; color:#d1d5db;">${item.thought || '-'}</td>
                    <td style="max-width:200px;">${dipBadge} <span style="font-style:italic; color:#93c5fd;">${item.diplomatic_message || ''}</span></td>
                    <td>${evChoiceBadge}</td>
                    <td><button class="btn-inspect" onclick="openModal(${originalIndex})">🔍 İncele</button></td>
                </tr>`;
            });
            tbody.innerHTML = rows;
        }

        function openModal(idx) {
            const item = telemetryData[idx];
            if (!item) return;

            document.getElementById("modalTitle").innerText = `Tur ${item.turn} — ${item.agent_name} (${item.latency_ms} ms)`;
            document.getElementById("modalThought").innerText = item.thought || "N/A";
            document.getElementById("modalBench").innerText = JSON.stringify(item.benchmark || {}, null, 2);
            document.getElementById("modalActions").innerText = JSON.stringify(item.actions || [], null, 2);
            document.getElementById("inspectModal").classList.add("active");
        }

        function closeModal() {
            document.getElementById("inspectModal").classList.remove("active");
        }

        setInterval(fetchStatus, 1000);
        fetchStatus();
    </script>
</body>
</html>
"""


class DashboardHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _GLOBAL_MANAGER
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            if _GLOBAL_MANAGER:
                data = {
                    "turn": _GLOBAL_MANAGER.current_turn,
                    "max_turns": _GLOBAL_MANAGER.max_turns,
                    "winner": _GLOBAL_MANAGER.winner,
                    "countries": [c.to_dict() for c in _GLOBAL_MANAGER.countries],
                    "telemetry": getattr(_GLOBAL_MANAGER, "telemetry_history", []),
                    "latest_decision": getattr(_GLOBAL_MANAGER, "latest_decision", None),
                }
            else:
                data = {"turn": 0, "countries": [], "telemetry": []}

            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_web_inspector(manager: "TurnManager", port: int = 8000) -> None:
    global _GLOBAL_MANAGER
    _GLOBAL_MANAGER = manager

    def run_server():
        try:
            server = HTTPServer(("0.0.0.0", port), DashboardHTTPHandler)
            print(f"\n>>> [CANLI WEB INSPECTOR]: http://localhost:{port} <<<\n")
            server.serve_forever()
        except Exception as e:
            print(f"Web Inspector baslatilamadi: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
