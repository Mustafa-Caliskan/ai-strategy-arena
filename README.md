# AI Strategy Arena

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Test Suite](https://img.shields.io/badge/tests-64%20passed-success)](https://github.com/Mustafa-Caliskan/ai-strategy-arena)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)

AI Strategy Arena is an open-source evaluation framework and simulation environment designed for benchmarking Large Language Models (LLMs) in long-horizon, incomplete-information macro-strategy domains.

---

## Overview

Evaluating frontier language models on static, single-turn prompts or deterministic board games fails to measure complex strategic behaviors such as multi-resource allocation, long-term infrastructure planning, spatial unit positioning, asynchronous diplomacy, contract compliance, and calculated betrayal.

AI Strategy Arena provides a deterministic simulation environment inspired by macro-strategy and multi-agent game theory. Agents operate under Fog of War and interact through physical entities, economic development, and natural language communication.

---

## Core System Architecture

The framework is decoupled into distinct layers: simulation engine, physical entity management, diplomatic contract verification, rule validation, and evaluation analytics.

```
ai_strategy_arena/
├── ai/                      # AI Provider interfaces, Prompt Builders, and Validation
│   ├── base_provider.py     # Base abstract class for LLM and algorithmic providers
│   ├── openai_provider.py   # OpenAI API provider (default: gpt-4o-mini)
│   ├── deepseek_provider.py # DeepSeek API provider (default: deepseek-chat / V4 Flash)
│   ├── baseline_agents.py   # Algorithmic baselines (Greedy, Defensive, Economic, Random)
│   ├── prompt_builder.py    # Fog-of-War state builder and prompt synthesizer
│   ├── response_parser.py   # Pydantic JSON parser with schema validation
│   └── action_validator.py  # 3-tier deterministic action and cost verification
│
├── game/                    # Core Game Engine and Mechanics
│   ├── map.py               # 2D Grid implementation with terrain types and structures
│   ├── pathfinding.py       # A* shortest path algorithm with terrain cost weighting
│   ├── entities.py          # ArmyEntity, EnvoyEntity, and spatial EntityManager
│   ├── resources.py         # Multi-resource state (Gold, Food, Wood, Stone, Iron, Influence)
│   ├── buildings.py         # Structure registry (Farm, Lumber Mill, Mine, Fort, Road, City)
│   ├── country.py           # Sovereign state attributes, garrisons, scores, and inboxes
│   ├── combat.py            # Resolution of field clashes, sieges, and territorial captures
│   ├── economy.py           # Resource yields, consumption rates, and population dynamics
│   ├── diplomacy.py         # Relational tracking, status transitions, and treaty checks
│   ├── contracts.py         # Formal pact engine with automated betrayal detection
│   └── game_state.py        # Perspective-filtered state serialization
│
├── benchmark/               # Benchmark Engine and Metric Profiling
│   ├── elo_system.py        # FIDE-standard Elo calculation framework
│   ├── benchmark_runner.py  # Deterministic round-robin tournament runner
│   └── behavioral_profiler.py # 6-Dimensional Strategic Behavioral Profiler
│
├── simulation/              # Simulation Execution and Event Pipeline
│   ├── turn_manager.py      # Turn orchestration, lifecycle hooks, and async coordinator
│   ├── event_system.py      # Structured JSONL decision logger and event bus
│   └── simulation_runner.py # Headless multi-seed batch execution harness
│
├── ui/                      # 2D Desktop Interface (Pygame)
│   ├── renderer.py          # Async-safe render loop
│   ├── map_view.py          # Spatial map renderer with structure overlays
│   ├── scoreboard.py        # Real-time resource metrics and active treaties
│   ├── event_log.py         # Event telemetry display
│   └── controls.py          # Simulation speed and lifecycle controls
│
├── tests/                   # Automated Pytest suite (64 unit and integration tests)
├── config/                  # Configuration files for game rules and agents
└── main.py                  # CLI entry point
```

---

## Key Capabilities

### 1. Multi-Resource and Infrastructural Economy
Agents manage six interdependent resources:
- **Gold:** Sovereign treasury used for expansion, military upkeep, and research.
- **Food:** Required for population sustenance; deficits cause military starvation.
- **Wood & Stone:** Primary building blocks for municipal and defensive structures.
- **Iron:** Requisite material for advanced weaponry and unit recruitment.
- **Influence:** Diplomatic currency required to ratify alliances and establish treaties.

Structures include `FARM`, `LUMBER_MILL`, `MINE`, `FORT`, `ROAD`, and `CITY`, each modifying local resource output and defense coefficients.

### 2. Spatial Entity Engine and Asynchronous Diplomacy
- **Field Armies (`ArmyEntity`):** Physical regiments with distinct positions, sizes, morale, and travel vectors. Armies can split, merge, intercept hostile forces, and lay siege to fortified enemy cities.
- **Traveling Envoys (`EnvoyEntity`):** Diplomatic correspondence and treaty proposals do not transfer instantaneously. Envoys traverse the map via A* pathfinding; communications are delivered only upon reaching the target capital.

### 3. Formal Contracts and Betrayal Detection
Agents can ratify formal binding pacts (`NON_AGGRESSION`, `TRADE_DEAL`, `DEFENSIVE_PACT`) with defined durations. If an agent attacks an active partner, the engine registers a betrayal event, decrements the agent's trustworthiness index, and records the breach for benchmark reporting.

### 4. 6-Dimensional Behavioral Profiling
Every simulation run tracks and analyzes agent actions across six standardized dimensions:
1. **Aggressiveness (AGG):** Rate of military mobilization, territorial expansion, and offensive engagements.
2. **Economic Focus (ECO):** Infrastructure expenditure, trade volume, and resource capitalization.
3. **Trustworthiness (TRU):** Treaty fulfillment rate and contract adherence.
4. **Adaptability (ADP):** Shannon entropy of action diversity under changing tactical conditions.
5. **Deception Index (DEC):** Frequency of opportunistically breaking active agreements.
6. **Long-Term Planning (LTP):** Research prioritization and permanent structure development.

---

## Action Space Specification

Each turn, agents receive a perspective-filtered JSON state and return a structured decision payload:

```json
{
  "action": "ATTACK | DEFEND | EXPAND | ECONOMY | RESEARCH | TRADE | DIPLOMACY | BUILD | RECRUIT | MOVE_ARMY | DISPATCH_ARMY",
  "target": "AI_B",
  "sub_action": "PEACE | TRADE | ALLIANCE | WAR | FARM | LUMBER_MILL | MINE | FORT | ROAD | CITY",
  "diplomatic_message": "Proposal for an 8-turn non-aggression pact to stabilize our shared border.",
  "reason": "Establishing defensive security while prioritizing mine construction."
}
```

---

## Baseline Agents

The framework includes four deterministic baseline agents for benchmarking:
- **Greedy Baseline:** Prioritizes military recruitment, expansion, and offensive strikes against vulnerable targets.
- **Defensive Baseline:** Prioritizes fortifications, boundary defense, and peace proposals.
- **Economic Baseline:** Optimizes resource production, cyclical municipal construction, and trade agreements.
- **Uniform Random Baseline:** Selects legal actions uniformly at random for baseline comparison.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Git

### Setup
```bash
git clone https://github.com/Mustafa-Caliskan/ai-strategy-arena.git
cd ai-strategy-arena
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and supply the relevant API keys:
```bash
cp .env.example .env
```

`.env` structure:
```ini
OPENAI_API_KEY=your_openai_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

---

## Usage

### Interactive 2D Interface (Pygame)
```bash
# DeepSeek vs OpenAI
python main.py --provider-a deepseek --provider-b openai --turns 100

# Algorithmic Baseline Match (Greedy vs Defensive)
python main.py --provider-a greedy --provider-b defensive --turns 100

# Random Baseline Match
python main.py --provider-a random --provider-b random --turns 100
```

### Headless Batch Execution
```bash
# Run headless batch simulation across 50 runs
python main.py --batch 50 --provider-a random --provider-b random
```

---

## Testing

The test suite covers action validation, economy balance, combat resolution, contract lifecycle, A* pathfinding, entity encounters, and behavioral profiling.

```bash
python -m pytest tests/ -v
```

```
============================== 64 passed in 11.60s ==============================
```

---

## Roadmap

- [ ] **Asymmetric Factions:** Faction specializations with variable production and military coefficients.
- [ ] **Multi-Agent Alliances:** Support for 4 to 8 agents, team formats (2v2), and dynamic coalition scenarios.
- [ ] **Regional Spawning:** Biome-specific spawn selections with tailored tactical trade-offs.
- [ ] **Adversarial Instigator Scenarios:** Controlled stress-testing of coalition stability under dedicated instigator agents.
- [ ] **Tile-Blending & Sprite Rendering:** Marching-squares terrain transitions and animated entity states.

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).
