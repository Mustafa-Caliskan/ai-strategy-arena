# ⚔️ AI Strategy Arena

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-64%20passed%20%2F%200%20failed-brightgreen.svg)](https://github.com/Mustafa-Caliskan/ai-strategy-arena)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pygame](https://img.shields.io/badge/UI-Pygame-red.svg)](https://www.pygame.org/)

**AI Strategy Arena** is a multi-agent strategy simulation and LLM benchmarking platform where Large Language Models (OpenAI GPT-4o-mini, DeepSeek V4 Flash, etc.) and algorithmic baseline agents compete, cooperate, negotiate, form binding pacts, bluff, and betray within a dynamic 2D strategy world.

---

## 📌 Project Overview

Traditional LLM benchmarks often evaluate models on static single-turn puzzles or chess/board games. **AI Strategy Arena** evaluates models in an **incomplete-information, long-horizon macro strategy environment** inspired by *Civilization*, *Catan*, *WorldBox*, and *Diplomacy*.

Models must balance:
1. **Multi-Resource Economy:** Managing Gold, Food, Wood, Stone, Iron, and Influence.
2. **Infrastructure Building:** Constructing Farms, Mines, Lumber Mills, Forts, Roads, and Cities.
3. **Physical Entity Engine:** Maneuvering field armies and dispatching diplomatic envoys across a 2D grid with A* pathfinding.
4. **Natural Language Diplomacy:** Exchanging letters with other LLMs, negotiating non-aggression treaties, trading resources, or launching surprise attacks.
5. **Contract & Betrayal Engine:** Formal non-aggression pacts with automated betrayal detection and diplomatic reliability tracking.

---

## 🌟 Key Features

* **Multi-Resource & Infrastructure Economy:** 6 distinct resources with specialized production structures (`FARM`, `LUMBER_MILL`, `MINE`, `FORT`, `ROAD`, `CITY`).
* **Physical Entity Engine (`ArmyEntity` & `EnvoyEntity`):**
  * Independent field armies that maneuver, split, merge, clash on tiles, and lay siege to enemy city garrisons.
  * Diplomatic envoys that physically travel across the map; letters and pact proposals are only delivered once the envoy reaches the destination city (**Delayed Diplomacy**).
  * Built-in lightweight **A\* Pathfinding** navigating terrain obstacles.
* **LLM-to-LLM Natural Language Messaging:** AI models compose diplomatic envoy messages delivered directly to recipient inboxes.
* **Binding Contracts & Betrayal Tracking:** Formal `NON_AGGRESSION`, `TRADE_DEAL`, and `DEFENSIVE_PACT` treaties. If an agent attacks an active partner, the engine logs a `🚨 [BETRAYAL]` event and penalizes their trustworthiness score.
* **Rule Compliance & Action Validation:** 3-stage validation pipeline ensuring zero illegal moves or hallucinated actions can break the simulation state.
* **6D Behavioral Radar Profiler:** Quantifies agent strategies across 6 core dimensions:
  * **Aggressiveness (`AGG`)**
  * **Economic Focus (`ECO`)**
  * **Trustworthiness (`TRU`)**
  * **Adaptability (`ADP`)**
  * **Deception Index (`DEC`)**
  * **Long-Term Planning (`LTP`)**
* **Deterministic Elo League & Tournament Runner:** Standard FIDE Elo ratings ($K=32$) with automated round-robin tournament execution.
* **Dual Execution Modes:** Async Pygame interactive 2D desktop renderer & high-speed headless batch execution.

---

## 🏗️ Project Architecture

```
ai_strategy_arena/
├── ai/                      # AI Providers, Parsers & Validation
│   ├── base_provider.py     # Abstract AIProvider base class
│   ├── openai_provider.py   # OpenAI GPT-4o-mini async integration
│   ├── deepseek_provider.py # DeepSeek V4 Flash / Chat async integration
│   ├── baseline_agents.py   # Greedy, Defensive, Economic, Random baseline bots
│   ├── prompt_builder.py    # Fog-of-War filtered system/user prompts
│   ├── response_parser.py   # Pydantic JSON parser with markdown extraction
│   └── action_validator.py  # 3-stage rule & resource validation engine
│
├── game/                    # Game Engine & Core Mechanics
│   ├── map.py               # 20x20 / 30x30 Grid with Terrain & Buildings
│   ├── pathfinding.py       # A* (A-Star) shortest path algorithm
│   ├── entities.py          # ArmyEntity, EnvoyEntity & EntityManager
│   ├── resources.py         # 6-resource dataclass & capacity logic
│   ├── buildings.py         # BuildingType, costs, and resource yields
│   ├── country.py           # Country state, garrison, score & inboxes
│   ├── combat.py            # Unit clashes, territory captures & city sieges
│   ├── economy.py           # Resource yields, population growth & starvation
│   ├── diplomacy.py         # Relations, statuses & contract manager
│   ├── contracts.py         # Formal pact lifecycle & betrayal engine
│   └── game_state.py        # Fog-of-war filtered perspective state JSON
│
├── benchmark/               # Benchmark Engine & Analytics
│   ├── elo_system.py        # FIDE Elo rating calculations & leaderboard
│   ├── benchmark_runner.py  # Round-robin tournament coordinator
│   └── behavioral_profiler.py # 6D Radar Behavioral Profiling engine
│
├── simulation/              # Simulation Loop & Event Management
│   ├── turn_manager.py      # Async turn coordination & entity lifecycle
│   ├── event_system.py      # JSONL decision logging & display narrative
│   └── simulation_runner.py # Headless batch runner
│
├── ui/                      # Pygame 2D Desktop Interface
│   ├── renderer.py          # Async-safe main render loop
│   ├── map_view.py          # 2D map view with buildings & road rendering
│   ├── scoreboard.py        # 6-resource HUD, diplomacy & active pacts
│   ├── event_log.py         # Real-time event & betrayal narrative
│   └── controls.py          # Speed multipliers, pause/resume controls
│
├── tests/                   # 64 Unit & Integration Tests (100% Passing)
├── config/                  # Game & Agent YAML configurations
└── main.py                  # CLI & Launcher entry point
```

---

## 🤖 Action Space

Each turn, an AI model receives an incomplete-information perspective JSON state and outputs a strict JSON decision:

```json
{
  "action": "ATTACK | DEFEND | EXPAND | ECONOMY | RESEARCH | TRADE | DIPLOMACY | BUILD | RECRUIT | MOVE_ARMY | DISPATCH_ARMY",
  "target": "AI_B",
  "sub_action": "PEACE | TRADE | ALLIANCE | WAR | FARM | LUMBER_MILL | MINE | FORT | ROAD | CITY",
  "diplomatic_message": "We propose a 10-turn non-aggression pact to secure our eastern borders.",
  "reason": "Economic development while securing peace."
}
```

---

## 📊 6D Behavioral Profiling & Archetypes

The profiler evaluates every decision and produces a comprehensive ASCII radar profile:

```text
┌────────────────────────────────────────────────────────┐
│ 📊 STRATEGIC RADAR PROFILE: DeepSeek-V3                │
│ Archetype: 🔥 Brutal Warmonger                         │
├────────────────────────────────────────────────────────┤
│  [AGG] Aggressiveness      :  82.4 / 100 ████████████░░░ │
│  [ECO] Economic Focus      :  35.0 / 100 █████░░░░░░░░░░ │
│  [TRU] Trustworthiness     :  25.0 / 100 ███░░░░░░░░░░░░ │
│  [ADP] Adaptability        :  68.2 / 100 ██████████░░░░░ │
│  [DEC] Deception Index     :  60.0 / 100 █████████░░░░░░ │
│  [LTP] Long-Term Planning  :  42.5 / 100 ██████░░░░░░░░░ │
└────────────────────────────────────────────────────────┘
```

**Archetypes:**
- `🔥 Brutal Warmonger`: High aggression, breaks pacts to conquer land.
- `⚔️ Honorable Champion`: Strong military presence, loyal to treaties.
- `💰 Merchant Prince`: Thrives on commerce, gold, and trade caravans.
- `🏛️ Scientific Architect`: Focuses on technology and permanent cities.
- `🎭 Cunning Instigator`: High deception, bluffs and betrays opportunistically.
- `🦎 Versatile Strategist`: Highly dynamic, adapts between defense and expansion.
- `⚖️ Pragmatic Sovereign`: Balanced strategy focused on survival.

---

## 🧪 Testing

The repository maintains an automated test suite verifying all game rules, combat calculations, contract breaches, and baseline behaviors:

```bash
python -m pytest tests/ -v
```

```
============================== 64 passed in 11.69s ==============================
```

---

## 🗺️ Roadmap & Future Game Modes

The following features are designed in the architecture and planned for upcoming phases:

- [ ] **Asymmetric Factions / Kingdoms:** Faction selection with unique passive perks (e.g. *Iron Legion* +20% army power, *Harvest Dynasty* +30% food yield).
- [ ] **Regional Map Spawning:** Players select starting biomes (coastal trade basins, mountain fortresses, dense woodlands).
- [ ] **Multiplayer Alliances:** 4–8 AI Free-For-All, 2v2 team matches, and 3v1 coalition scenarios.
- [ ] **Chaos Lord / Instigator AI Mode:** An aggressive AI designed to provoke wars, forcing other models to forge emergency defensive coalitions.
- [ ] **WorldBox Pixel Art & Tile Blending:** Marching squares smooth borders, animated army banners, and traveling envoy sprites.

---

## ⚡ Installation & Quickstart

### 1. Clone the Repository
```bash
git clone https://github.com/Mustafa-Caliskan/ai-strategy-arena.git
cd ai-strategy-arena
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
OPENAI_API_KEY=your_openai_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 4. Run Interactive 2D Game (Pygame UI)
```bash
# DeepSeek vs GPT-4o-mini
python main.py --provider-a deepseek --provider-b openai --turns 100

# Fast test mode (Random bot vs Random bot)
python main.py --provider-a random --provider-b random --turns 100
```

### 5. Run Headless Batch Simulation
```bash
python main.py --batch 50 --provider-a random --provider-b random
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
