"""
launch_game.py — OpenAI vs DeepSeek Wesnoth Benchmark Başlatıcı

Tek komutla:
1. Python Benchmark Sunucusunu (OpenAI & DeepSeek API dinleyicisi) başlatır.
2. Battle for Wesnoth oyununu açar.
"""
import subprocess
import time
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WESNOTH_EXE = ROOT_DIR.parent / "wesnoth" / "wesnoth.exe"
SERVER_SCRIPT = ROOT_DIR / "wesnoth_bridge" / "benchmark_server.py"

def main():
    print("=" * 60)
    print("⚔️ BATTLE FOR WESNOTH -- AI BENCHMARK ARENA LAUNCHER")
    print("=" * 60)

    if not WESNOTH_EXE.exists():
        print(f"[!] wesnoth.exe not found at: {WESNOTH_EXE}")
        return

    # 1. Benchmark Sunucusunu Arka Planda Başlat
    print("[+] Starting Python AI Benchmark Server (OpenAI & DeepSeek)...")
    server_proc = subprocess.Popen([sys.executable, str(SERVER_SCRIPT)])
    time.sleep(1.0)

    # 2. Wesnoth Oyununu Başlat
    print("[+] Launching Battle for Wesnoth...")
    print("   Select: Multiplayer -> Local Game -> 'AI Benchmark Arena'")
    print("=" * 60)

    try:
        subprocess.run([str(WESNOTH_EXE)], cwd=str(WESNOTH_EXE.parent))
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Stopping Benchmark Server...")
        server_proc.terminate()
        print("[+] Session complete! Check logs/benchmark/ for report.")

if __name__ == "__main__":
    main()