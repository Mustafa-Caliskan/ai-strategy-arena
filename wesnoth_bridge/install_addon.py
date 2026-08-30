import os
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WESNOTH_DIR = ROOT_DIR.parent / "wesnoth"
ADDON_SOURCE = ROOT_DIR / "wesnoth_bridge" / "add_on"
SCENARIO_SRC = ADDON_SOURCE / "scenarios" / "2p_AI_Benchmark.cfg"
LUA_SRC = ADDON_SOURCE / "lua" / "ai_arena_bridge.lua"

def install():
    print("=" * 60)
    print("[*] BATTLE FOR WESNOTH -- AI ARENA INSTALLER")
    print("=" * 60)

    if not WESNOTH_DIR.exists():
        print(f"[!] Wesnoth directory not found: {WESNOTH_DIR}")
        return

    # 1. Add-on klasörüne yükle
    addons_target = WESNOTH_DIR / "data" / "add-ons" / "AI_Arena"
    addons_target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ADDON_SOURCE, addons_target, dirs_exist_ok=True)
    print(f"[+] Add-on installed to: {addons_target}")

    # 2. Doğrudan data/lua klasörüne kopyala (wesnoth.require doğrudan bulsun)
    core_lua = WESNOTH_DIR / "data" / "lua"
    if core_lua.exists() and LUA_SRC.exists():
        shutil.copy(LUA_SRC, core_lua / "ai_arena_bridge.lua")
        print(f"[+] Lua bridge installed to core: {core_lua / 'ai_arena_bridge.lua'}")

    # 3. Doğrudan Multiplayer Senaryoları klasörüne kopyala
    mp_scenarios = WESNOTH_DIR / "data" / "multiplayer" / "scenarios"
    if mp_scenarios.exists() and SCENARIO_SRC.exists():
        shutil.copy(SCENARIO_SRC, mp_scenarios / "2p_AI_Benchmark.cfg")
        print(f"[+] Scenario added: {mp_scenarios / '2p_AI_Benchmark.cfg'}")

    print("=" * 60)
    print("[+] INSTALLATION & FIX COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    install()