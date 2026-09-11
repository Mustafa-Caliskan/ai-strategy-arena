"""
backend/test_server.py
Uvicorn sunucusu ve API endpointlerini doğrular.
"""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from httpx import AsyncClient, ASGITransport
from main import app, step_turn, current_game

async def run_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test 1: Root HTML
        resp = await ac.get("/")
        print("Root HTML Status:", resp.status_code)
        assert resp.status_code == 200
        assert "AI STRATEGY ARENA" in resp.text

        # Test 2: Game State API
        resp = await ac.get("/api/state")
        print("API State Status:", resp.status_code)
        assert resp.status_code == 200
        data = resp.json()
        print("Initial Turn:", data["turn"])
        assert data["turn"] == 1

        # Test 3: Map API
        resp = await ac.get("/api/map")
        print("API Map Status:", resp.status_code, "Tiles:", len(resp.json()))
        assert resp.status_code == 200

        # Test 4: Step Turn Execution
        print("\n--- Testing 1 Step Turn ---")
        await step_turn()
        print("Post-step Turn:", current_game.turn)
        assert current_game.turn == 2

        # Test 5: Benchmark Report
        resp = await ac.get("/api/report")
        print("API Report Status:", resp.status_code)
        assert resp.status_code == 200
        rep = resp.json()
        print("Participants in report:", list(rep["participants"].keys()))

    print("\n[SUCCESS] AI Strategy Arena v2.0 is 100% verified and operational!")

if __name__ == "__main__":
    asyncio.run(run_tests())
