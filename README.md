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
├── ai/                      # Frontier AI Providers & Strategic Evaluators
│   ├── base_provider.py     # Base abstract class for LLM providers
│   ├── claude_provider.py   # Anthropic Claude API provider (Claude Sonnet 5 / 3.7 Sonnet)
│   ├── anthropic_provider.py# Anthropic compatibility wrapper
│   ├── openai_provider.py   # OpenAI API provider (gpt-4o-mini / gpt-4o)
│   ├── deepseek_provider.py # DeepSeek API provider (deepseek-chat)
│   ├── prompt_builder.py    # Multi-rival state builder and prompt synthesizer
│   └── response_parser.py   # Pydantic JSON parser with schema validation
│
├── backend/                 # 3-Way Tri-Polar Simulation & WebSocket Server
│   ├── ai/                  # Asynchronous multi-model LLM bridge
│   │   ├── llm_bridge.py    # Parallel frontier LLM dispatcher (Claude, OpenAI, DeepSeek)
│   │   └── prompt_builder.py# Fog-of-War tactical prompt synthesizer
│   ├── game/                # Tri-Polar Hexagonal Engine
│   │   ├── engine.py        # Bilateral treaties, 6-way envoy state machine & turn loop
│   │   ├── map.py           # 28x18 Hexagonal map with 3 Keeps and Fog of War
│   │   └── state.py         # Tri-polar sovereign factions, resources, and diplomacy
│   ├── benchmark/           # 6-Dimensional Radar Profiler
│   │   └── evaluator.py     # Real-time military, economic, and diplomatic scoring
│   ├── static/              # Modern Dark Tactical Web Interface
│   │   ├── index.html       # Live canvas, 3 HUD faction cards, and radar chart
│   │   ├── style.css        # Responsive cyber-tactical CSS
│   │   ├── app.js           # WebSocket streaming and canvas renderer
│   │   └── assets/          # Faction leader and terrain sprites
│   ├── main.py              # FastAPI server with WebSocket live stream
│   └── test_server.py       # Automated integration and benchmark test suite
│
├── start.bat                # 1-Click launcher (starts server and opens browser)
├── OYNA_3_Model_Arenasi.bat # Alternative 1-click arena launcher
├── requirements.txt         # Minimal production dependencies
└── README.md                # Documentation and benchmark specifications
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

## Multi-Agent Frontier LLM Benchmark Matrix

AI Strategy Arena benchmarks frontier language models—including **Anthropic Claude**, **OpenAI GPT-4o**, and **DeepSeek**—across long-horizon game-theoretic domains:

- **Frontier Model Providers (`ai/`):** First-class asynchronous providers with strict schema enforcement:
  - `ClaudeProvider` (`ai/claude_provider.py`): Leverages Anthropic Claude (Sonnet 5 / 3.7 Sonnet) with extended thinking and structured decision output.
  - `OpenAIProvider` (`ai/openai_provider.py`): OpenAI API provider with JSON-mode schema validation (default: `gpt-4o-mini` / `gpt-4o`).
  - `DeepSeekProvider` (`ai/deepseek_provider.py`): DeepSeek reasoning and chat provider for high-speed tactical evaluation.
- **Long-Term Strategic Planning (LTP):** Benchmarking multi-turn infrastructural resource allocation (farms, mines, forts) and technology tree milestones under dynamic economic constraints.
- **Asymmetric Diplomacy (ADP):** Evaluating handling of incomplete information and Fog of War, including strategic bluffing, non-aggression negotiation, and traveling envoy correspondence.
- **Contract Fidelity & Betrayal Dynamics (TRU & DEC):** Studying game-theoretic loyalty vs. opportunism—measuring whether models honor ratified pacts under military pressure or execute opportunistic breaches.
- **Extended Thinking & Deliberation:** Built-in capability for frontier models to deliberate on complex geopolitical turns before emitting validated action schemas.

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
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-5
```

---

## Usage

### 1-Click Launch (Browser & Interactive Web Dashboard)
Double-click `OYNA_3_Model_Arenasi.bat` (or `start.bat`), or run via terminal:
```bash
python start.py
```
This automatically boots the FastAPI backend and opens the tactical dashboard in your default browser at `http://localhost:8000`.

### Manual CLI Server
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Testing & Verification

The suite includes end-to-end API, state transition, and multi-model parallel inference verification:

```bash
python backend/test_server.py
```

```text
Root HTML Status: 200
API State Status: 200
Initial Turn: 1
API Map Status: 200 Tiles: 504
--- Testing 1 Step Turn ---
Post-step Turn: 2
API Report Status: 200
Participants in report: ['side_1', 'side_2', 'side_3']

[SUCCESS] AI Strategy Arena is 100% verified and operational!
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
