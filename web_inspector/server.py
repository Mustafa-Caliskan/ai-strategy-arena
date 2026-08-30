"""
server.py — AI Strategy Arena Canli Web Telemetri ve API Inspector Sunucusu

Tarayicida http://localhost:8000 adresinde:
1. OpenAI ve DeepSeek modellerine giden GERCEK promptlari (System & User Prompt)
2. Modellerden donen HAM API JSON yanitlarini
3. Gecikme surelerini (Latency ms) ve stratejik dusunceleri
4. Kara Sancaklilar (Bandits) saldiri kayitlarini
canli olarak gosterir.
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
    <title>⚡ AI Strategy Arena — Canlı API & Telemetri Inspector</title>
    <style>
        :root {
            --bg-dark: #0f111a;
            --bg-card: #181b26;
            --bg-card-hover: #222636;
            --border-color: #2b3044;
            --text-main: #e8ecf4;
            --text-muted: #8c96ac;
            --accent-openai: #3b82f6;
            --accent-deepseek: #ef4444;
            --accent-bandit: #111827;
            --accent-gold: #f59e0b;
            --accent-green: #10b981;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            padding: 24px;
            font-size: 14px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
        }
        .header h1 { font-size: 24px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .badge-live {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            position: relative;
            overflow: hidden;
        }
        .stat-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
        }
        .stat-card.openai::before { background: var(--accent-openai); }
        .stat-card.deepseek::before { background: var(--accent-deepseek); }
        .stat-card.bandits::before { background: #6b7280; }

        .stat-card h3 { font-size: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; }
        .stat-row { display: flex; justify-content: space-between; margin-bottom: 6px; color: var(--text-muted); }
        .stat-val { color: var(--text-main); font-weight: 600; }

        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }

        .table-container {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 24px;
        }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: #131620; padding: 12px 16px; font-weight: 600; color: var(--text-muted); border-bottom: 1px solid var(--border-color); }
        td { padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        tr:hover { background: var(--bg-card-hover); }

        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }
        .tag-openai { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .tag-deepseek { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .tag-bandit { background: rgba(107, 114, 128, 0.3); color: #9ca3af; }

        .btn-inspect {
            background: #2b3044;
            color: #fff;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .btn-inspect:hover { background: #3b82f6; }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(4px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            width: 900px;
            max-width: 100%;
            max-height: 88vh;
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
        .modal-body {
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .code-box {
            background: #0d0f17;
            border: 1px solid #232738;
            border-radius: 8px;
            padding: 14px;
            font-family: "Consolas", monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
            color: #d1d5db;
            max-height: 250px;
            overflow-y: auto;
        }
        .code-title { font-weight: 600; color: var(--accent-gold); margin-bottom: 6px; font-size: 13px; }
        .btn-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 20px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ AI Strategy Arena — Canlı Telemetri & API Denetleyicisi</h1>
        <div class="badge-live">● CANLI YAYIN (1s Yenileme)</div>
    </div>

    <div class="stats-grid" id="statsGrid">
        <!-- JS ile dolacak -->
    </div>

    <div class="section-title">🔍 Gerçek Zamanlı LLM Çağrıları & API Yanıtları (Canlı Akış)</div>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Tur</th>
                    <th>Model / Taraf</th>
                    <th>Seçilen Eylem</th>
                    <th>Gecikme</th>
                    <th>Stratejik Düşünce (Thought)</th>
                    <th>Mektup</th>
                    <th>API Detay</th>
                </tr>
            </thead>
            <tbody id="telemetryTable">
                <tr><td colspan="7" style="text-align:center; color:#8c96ac;">API verileri bekleniyor...</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Inspector Modal -->
    <div class="modal" id="inspectModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">API Çağrı Detayları</h3>
                <button class="btn-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div>
                    <div class="code-title">📜 MODELE GİDEN SYSTEM PROMPT:</div>
                    <div class="code-box" id="modalSystemPrompt"></div>
                </div>
                <div>
                    <div class="code-title">📦 MODELE GİDEN OYUN DURUMU (USER PROMPT):</div>
                    <div class="code-box" id="modalUserPrompt"></div>
                </div>
                <div>
                    <div class="code-title">💬 MODELİN DÖNDÜRDÜĞÜ HAM JSON YANITI (RAW API RESPONSE):</div>
                    <div class="code-box" id="modalRawResponse" style="color: #34d399;"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let telemetryData = [];

        async function fetchStatus() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();
                renderStats(data);
                renderTelemetry(data.telemetry || []);
            } catch (e) {
                console.error(e);
            }
        }

        function renderStats(data) {
            const grid = document.getElementById("statsGrid");
            if (!data.countries) return;

            let html = "";
            data.countries.forEach(c => {
                const isOAI = c.agent_id === "AI_A";
                const isBandit = c.agent_id === "BANDITS";
                const cardClass = isBandit ? "bandits" : (isOAI ? "openai" : "deepseek");
                const crest = isBandit ? "💀" : (isOAI ? "🔵" : "🔴");

                html += `
                <div class="stat-card ${cardClass}">
                    <h3><span>${crest} ${c.name}</span> <span style="font-size:12px; color:var(--text-muted);">Skor: ${c.score}</span></h3>
                    <div class="stat-row"><span>Altın / Erzak:</span><span class="stat-val">${Math.round(c.resources.gold)} 💰 / ${Math.round(c.resources.food)} 🍞</span></div>
                    <div class="stat-row"><span>Ordu Gücü:</span><span class="stat-val">${c.resources.army} ⚔️</span></div>
                    <div class="stat-row"><span>Toprak Sayısı:</span><span class="stat-val">${c.resources.territory} 🏰</span></div>
                    <div class="stat-row"><span>Durum:</span><span class="stat-val">${c.status.toUpperCase()}</span></div>
                </div>`;
            });
            grid.innerHTML = html;
        }

        function renderTelemetry(list) {
            telemetryData = list;
            const tbody = document.getElementById("telemetryTable");
            if (!list || list.length === 0) return;

            let rows = "";
            // En yeni kayıtlar üstte
            [...list].reverse().forEach((item, idx) => {
                const originalIndex = list.length - 1 - idx;
                const isOAI = item.agent_id === "AI_A";
                const isBandit = item.agent_id === "BANDITS";
                const tagClass = isBandit ? "tag-bandit" : (isOAI ? "tag-openai" : "tag-deepseek");

                rows += `
                <tr>
                    <td><strong>T${item.turn}</strong></td>
                    <td><span class="tag ${tagClass}">${item.agent_name}</span></td>
                    <td><code style="color:var(--accent-gold); font-weight:bold;">${item.action} ${item.sub_action || ''}</code></td>
                    <td><span style="color:#10b981;">${item.latency_ms} ms</span></td>
                    <td style="max-width:300px; color:#d1d5db;">${item.thought || '-'}</td>
                    <td style="max-width:200px; font-style:italic; color:#93c5fd;">${item.diplomatic_message || '-'}</td>
                    <td><button class="btn-inspect" onclick="openModal(${originalIndex})">🔍 İncele</button></td>
                </tr>`;
            });
            tbody.innerHTML = rows;
        }

        function openModal(idx) {
            const item = telemetryData[idx];
            if (!item) return;

            document.getElementById("modalTitle").innerText = `Tur ${item.turn} — ${item.agent_name} (${item.latency_ms} ms)`;
            document.getElementById("modalSystemPrompt").innerText = item.system_prompt || "N/A";
            document.getElementById("modalUserPrompt").innerText = item.user_prompt || "N/A";
            document.getElementById("modalRawResponse").innerText = item.raw_response || "N/A";
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
        # Sessiz loglama
        return


def start_web_inspector(manager: "TurnManager", port: int = 8000) -> None:
    """Arka planda http://localhost:8000 uzerinde web inspector sunucusunu baslatir."""
    global _GLOBAL_MANAGER
    _GLOBAL_MANAGER = manager

    def run_server():
        try:
            server = HTTPServer(("0.0.0.0", port), DashboardHTTPHandler)
            print(f"\n>>> [CANLI WEB INSPECTOR BASLATILDI]: http://localhost:{port} adresinden prompt ve API yanitlarini izleyebilirsiniz! <<<\n")
            server.serve_forever()
        except Exception as e:
            print(f"Web Inspector baslatilamadi: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()