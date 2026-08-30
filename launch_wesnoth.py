"""
launch_wesnoth.py — 1-Tıkla Battle for Wesnoth LLM Arena Başlatıcı
"""
import os
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent
WESNOTH_EXE   = BASE_DIR.parent / "wesnoth" / "wesnoth.exe"
BRIDGE_SCRIPT = BASE_DIR / "wesnoth_bridge" / "server.py"

def main():
    print("=" * 65)
    print("👑 BATTLE FOR WESNOTH: 3-WAY LLM ARENA")
    print("   🔵 Side 1: OpenAI (GPT-4o)")
    print("   🔴 Side 2: DeepSeek")
    print("   💀 Side 3: Kara Sancaklı Haydutlar (Bandits)")
    print("=" * 65)

    if not WESNOTH_EXE.exists():
        print(f"HATA: wesnoth.exe bulunamadi: {WESNOTH_EXE}")
        sys.exit(1)

    print("\n[1/2] Python Bridge & Web Inspector baslatiliyor...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    bridge_proc = subprocess.Popen([sys.executable, str(BRIDGE_SCRIPT)], env=env)
    time.sleep(2.0)
    print("      >>> http://localhost:8000  (Canli API Inspector) <<<")

    print("\n[2/2] Battle for Wesnoth aciliyor...")
    print("      3-Way AI Arena senaryosu otomatik calisacak!\n")

    cmd = [
        str(WESNOTH_EXE),
        "--unsafe-scripts",
        "--multiplayer",
        "--scenario=multiplayer_3p_AI_Arena"
    ]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        bridge_proc.terminate()
        print("\nOyun bitti. Bridge kapatildi.")

if __name__ == "__main__":
    main()
