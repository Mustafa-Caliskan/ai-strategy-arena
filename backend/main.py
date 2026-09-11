"""
backend/main.py
FastAPI Uygulaması & WebSocket Canlı Yayın Motoru v3.0
3 Krallık Savaş Arenası: OpenAI vs DeepSeek vs Anthropic Claude
"""
from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from game.state import GameState, SideState, DiplomaticStatus
from game.engine import GameEngine
from game.map import ArenaMap
from ai.prompt_builder import PromptBuilder
from ai.llm_bridge import LLMBridge
from benchmark.evaluator import generate_benchmark_report

app = FastAPI(title="AI Strategy Arena v3.0 — 3 Krallık", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Global Değişkenler & Bağlantı Yöneticisi
# ──────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        data = json.dumps(message, ensure_ascii=False)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
game_map = ArenaMap(cols=28, rows=18)
llm_bridge = LLMBridge()

# Varsayılan 3 Krallık Oyun Durumu
def create_initial_state() -> GameState:
    session_id = time.strftime("%Y%m%d_%H%M%S")
    s1 = SideState(
        id=1,
        name="OpenAI İmparatorluğu",
        model="gpt-4o-mini",
        color="#38bdf8",
        keep_x=13, keep_y=2
    )
    s2 = SideState(
        id=2,
        name="DeepSeek Orman Krallığı",
        model="deepseek-chat",
        color="#f43f5e",
        keep_x=21, keep_y=15
    )
    s3 = SideState(
        id=3,
        name="Anthropic Claude Bilgeliği",
        model=llm_bridge.anthropic_model,
        color="#f59e0b",
        keep_x=5, keep_y=15
    )
    return GameState(
        session_id=session_id,
        sides={1: s1, 2: s2, 3: s3}
    )

current_game = create_initial_state()
engine = GameEngine(current_game)
game_loop_task: asyncio.Task | None = None
is_paused = True


# ──────────────────────────────────────────────
# WebSocket Endpoint
# ──────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    init_payload = {
        "type": "INIT_STATE",
        "map": game_map.serialize(),
        "state": serialize_game_state(current_game)
    }
    await websocket.send_text(json.dumps(init_payload, ensure_ascii=False))
    try:
        while True:
            data = await websocket.receive_text()
            cmd = json.loads(data)
            action = cmd.get("action")
            if action == "START":
                await start_game_loop()
            elif action == "PAUSE":
                await pause_game_loop()
            elif action == "STEP":
                await step_turn()
            elif action == "RESET":
                await reset_game()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ──────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────
@app.get("/api/state")
async def get_state():
    return serialize_game_state(current_game)

@app.get("/api/map")
async def get_map():
    return game_map.serialize()

@app.get("/api/report")
async def get_report():
    return generate_benchmark_report(current_game)

@app.post("/api/game/start")
async def api_start():
    await start_game_loop()
    return {"status": "started"}

@app.post("/api/game/pause")
async def api_pause():
    await pause_game_loop()
    return {"status": "paused"}

@app.post("/api/game/step")
async def api_step():
    await step_turn()
    return {"status": "stepped"}

@app.post("/api/game/reset")
async def api_reset():
    await reset_game()
    return {"status": "reset"}


# ──────────────────────────────────────────────
# Oyun Döngüsü Mantığı (3 Taraf İçin Game Loop)
# ──────────────────────────────────────────────
async def step_turn():
    global current_game, engine
    gs = current_game

    # 1. Tur Başı Sayaçları & Canlı Olaylar
    turn_events = engine.advance_turn_counters()
    gs.active_world_event = PromptBuilder.get_world_event(gs.turn)
    gs.current_decision_event = PromptBuilder.get_decision_event(gs.turn)

    await manager.broadcast({
        "type": "TURN_STARTED",
        "turn": gs.turn,
        "world_event": gs.active_world_event,
        "decision_event": gs.current_decision_event,
        "events": turn_events
    })

    # 2. Üç Modelden Paralel Karar Toplama
    tasks = []
    for side_id in (1, 2, 3):
        side = gs.sides[side_id]
        sys_prompt = PromptBuilder.build_system_prompt(side, gs)
        user_prompt = PromptBuilder.build_user_prompt(side, gs)
        fallback_role = "aggressive" if side_id == 1 else ("economic" if side_id == 2 else "mystic_tactician")
        tasks.append(llm_bridge.get_decision(side.model, sys_prompt, user_prompt, fallback_role=fallback_role))

    results = await asyncio.gather(*tasks)

    # 3. Kararları Uygulama ve Olayları Yayma
    for i, side_id in enumerate((1, 2, 3)):
        orders = results[i]
        applied_events = engine.apply_orders(side_id, orders)

        log_entry = {
            "turn": gs.turn,
            "side_id": side_id,
            "name": gs.sides[side_id].name,
            "thought": orders.get("thought", ""),
            "proposal": orders.get("diplomacy", {}).get("proposal"),
            "target": orders.get("diplomacy", {}).get("target"),
            "message": orders.get("diplomacy", {}).get("message"),
            "actions": orders.get("actions", []),
            "latency_ms": orders.get("_latency_ms", 0),
            "events": applied_events
        }
        gs.turn_log.append(log_entry)

        await manager.broadcast({
            "type": "DECISION_APPLIED",
            "log": log_entry,
            "state": serialize_game_state(gs)
        })

    # 4. Tur Tamamlandı
    await manager.broadcast({
        "type": "TURN_COMPLETED",
        "turn": gs.turn,
        "state": serialize_game_state(gs),
        "report": generate_benchmark_report(gs)
    })

    gs.turn += 1


async def run_game_loop():
    global is_paused
    while not is_paused:
        await step_turn()
        await asyncio.sleep(2.8)


async def start_game_loop():
    global is_paused, game_loop_task
    if is_paused:
        is_paused = False
        game_loop_task = asyncio.create_task(run_game_loop())
        await manager.broadcast({"type": "STATUS_CHANGED", "status": "running"})

async def pause_game_loop():
    global is_paused, game_loop_task
    is_paused = True
    if game_loop_task:
        game_loop_task.cancel()
        game_loop_task = None
    await manager.broadcast({"type": "STATUS_CHANGED", "status": "paused"})

async def reset_game():
    global current_game, engine
    await pause_game_loop()
    current_game = create_initial_state()
    engine = GameEngine(current_game)
    await manager.broadcast({
        "type": "RESET_COMPLETED",
        "state": serialize_game_state(current_game)
    })


def serialize_game_state(gs: GameState) -> dict:
    t = gs.turn
    sides_data = {}

    for k, s in gs.sides.items():
        b = s.compute_benchmark(t)
        sides_data[str(k)] = {
            "id": s.id,
            "name": s.name,
            "model": s.model,
            "color": s.color,
            "gold": s.resources.gold,
            "wood": s.resources.wood,
            "stone": s.resources.stone,
            "units": s.units,
            "workers": s.workers,
            "ships": s.ships,
            "spies": s.spies,
            "farms": s.buildings.farms,
            "mines": s.buildings.mines,
            "barracks": s.buildings.barracks,
            "forts": s.buildings.forts,
            "ports": s.buildings.ports,
            "tech": {"military": s.tech.military, "economic": s.tech.economic, "naval": s.tech.naval},
            "benchmark": {
                "AGG": b.agg, "ECO": b.eco, "TRU": b.tru,
                "ADP": b.adp, "DEC": b.dec, "LTP": b.ltp
            }
        }

    relations_data = {
        k: {
            "status": rel.status.value,
            "pact_turns": rel.pact_turns,
            "war_turns": rel.war_turns
        }
        for k, rel in gs.relations.items()
    }

    return {
        "session_id": gs.session_id,
        "turn": gs.turn,
        "is_paused": is_paused,
        "relations": relations_data,
        "first_contact": gs.first_contact_made,
        "island_controller": gs.island_controller_name(),
        "envoys": {
            k: {
                "phase": e.phase.value,
                "proposal": e.proposal,
                "message": e.message,
                "from_side": e.from_side,
                "to_side": e.to_side
            }
            for k, e in gs.envoys.items()
        },
        "sides": sides_data
    }


# Static web client mounting
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
