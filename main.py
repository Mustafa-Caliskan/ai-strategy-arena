"""
main.py — AI Strategy Arena Giriş Noktası

Kullanım:
  python main.py                    # Varsayılan: random AI ile test
  python main.py --batch 10         # 10 oyun batch simülasyon
  python main.py --turns 50         # 50 tur sınırı
  python main.py --seed 42          # Belirli seed
  python main.py --headless         # UI olmadan çalış
"""
from __future__ import annotations
import argparse
import asyncio
import logging
import sys
import os

from dotenv import load_dotenv

# .env yükle
load_dotenv()

# Loglama ayarla
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(description="AI Strategy Arena")
    parser.add_argument("--batch", type=int, default=0,
                        help="Batch simülasyon sayısı (0 = tek oyun)")
    parser.add_argument("--turns", type=int, default=200,
                        help="Maksimum tur sayısı")
    parser.add_argument("--seed", type=int, default=None,
                        help="Rastgelelik seed'i")
    parser.add_argument("--headless", action="store_true",
                        help="UI olmadan çalış")
    parser.add_argument("--provider-a", type=str, default="random",
                        choices=["random", "greedy", "defensive", "economic", "openai", "deepseek", "anthropic", "google"],
                        help="AI_A sağlayıcısı")
    parser.add_argument("--provider-b", type=str, default="random",
                        choices=["random", "greedy", "defensive", "economic", "openai", "deepseek", "anthropic", "google"],
                        help="AI_B sağlayıcısı")
    return parser.parse_args()


def make_provider(agent_id: str, provider_type: str, seed=None):
    """Provider factory — config'e göre doğru sağlayıcıyı oluştur."""
    from ai.random_provider import RandomProvider

    if provider_type == "random":
        return RandomProvider(agent_id=agent_id, seed=seed)

    elif provider_type == "greedy":
        from ai.baseline_agents import GreedyProvider
        return GreedyProvider(agent_id=agent_id, seed=seed)

    elif provider_type == "defensive":
        from ai.baseline_agents import DefensiveProvider
        return DefensiveProvider(agent_id=agent_id, seed=seed)

    elif provider_type == "economic":
        from ai.baseline_agents import EconomicProvider
        return EconomicProvider(agent_id=agent_id, seed=seed)

    elif provider_type == "openai":
        from ai.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not set in .env")
            sys.exit(1)
        return OpenAIProvider(agent_id=agent_id, api_key=api_key)

    elif provider_type == "deepseek":
        from ai.deepseek_provider import DeepSeekProvider
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.error("DEEPSEEK_API_KEY not set in .env")
            sys.exit(1)
        return DeepSeekProvider(agent_id=agent_id, api_key=api_key)

    elif provider_type == "anthropic":
        from ai.anthropic_provider import AnthropicProvider
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not set in .env")
            sys.exit(1)
        return AnthropicProvider(agent_id=agent_id, api_key=api_key)

    elif provider_type == "google":
        from ai.google_provider import GoogleProvider
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not set in .env")
            sys.exit(1)
        return GoogleProvider(agent_id=agent_id, api_key=api_key)

    else:
        raise ValueError(f"Unknown provider: {provider_type}")


def run_batch(args):
    """Headless batch simülasyon modu."""
    from simulation.simulation_runner import SimulationRunner

    logger.info(f"Starting batch simulation: {args.batch} runs, {args.turns} turns each")

    def provider_factory(agent_id: str, seed: int):
        ptype = args.provider_a if agent_id == "AI_A" else args.provider_b
        return make_provider(agent_id, ptype, seed)

    runner = SimulationRunner(
        provider_factory=provider_factory,
        max_turns=args.turns,
        base_seed=args.seed or 42,
    )
    report = runner.run_batch(args.batch)
    report.print_report()


async def run_single_headless(args):
    """Tek oyun, headless (UI yok), konsol çıktısı."""
    from game.country import create_default_countries
    from game.map import GameMap
    from simulation.turn_manager import TurnManager

    seed = args.seed
    countries = create_default_countries()
    game_map = GameMap(seed=seed)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)

    providers = {
        "AI_A": make_provider("AI_A", args.provider_a, seed),
        "AI_B": make_provider("AI_B", args.provider_b, seed),
    }

    logger.info(f"Starting headless game: AI_A={args.provider_a}, AI_B={args.provider_b}")

    manager = TurnManager(
        countries=countries,
        providers=providers,
        game_map=game_map,
        max_turns=args.turns,
        seed=seed,
    )

    def on_turn(tm):
        if tm.current_turn % 10 == 0:
            for c in tm.countries:
                r = c.resources
                logger.info(
                    f"T{tm.current_turn:03d} | {c.agent_id}: "
                    f"Gold={r.gold:.0f} Food={r.food:.0f} "
                    f"Army={r.army} Territory={r.territory} Tech={r.technology}"
                )

    winner, reason = await manager.run_game_async(on_turn_complete=on_turn)
    print(f"\n{'='*50}")
    print(f"GAME OVER — Winner: {winner} ({reason})")
    print(f"Turns played: {manager.current_turn}")
    for c in manager.countries:
        print(f"  {c.agent_id}: Score={c.calculate_score():.0f} | {c.to_dict()['resources']}")
    stats = manager.events.get_action_stats()
    print(f"\nAction Statistics:")
    for agent, actions in stats.items():
        total = sum(actions.values())
        print(f"  {agent}:")
        for action, count in sorted(actions.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            print(f"    {action:12s}: {count:3d} ({pct:.1f}%)")
    print("="*50)


async def run_ui(args):
    """Pygame UI modu — simülasyon ve render birlikte çalışır."""
    from game.country import create_default_countries
    from game.map import GameMap
    from simulation.turn_manager import TurnManager
    from ui.renderer import GameRenderer

    seed = args.seed
    countries = create_default_countries()
    game_map = GameMap(seed=seed)
    for c in countries:
        c.resources.territory = game_map.get_territory_count(c.agent_id)

    providers = {
        "AI_A": make_provider("AI_A", args.provider_a, seed),
        "AI_B": make_provider("AI_B", args.provider_b, seed),
    }

    logger.info(f"Starting UI game: AI_A={args.provider_a}, AI_B={args.provider_b}")

    manager = TurnManager(
        countries=countries,
        providers=providers,
        game_map=game_map,
        max_turns=args.turns,
        seed=seed,
    )

    renderer = GameRenderer()
    renderer.set_manager(manager)

    # Simülasyon + render eş zamanlı çalışır
    await asyncio.gather(
        manager.run_game_async(),
        renderer.run_async(manager),
    )

    # Oyun bittikten sonra ekran birkaç saniye kalır
    logger.info(f"Game ended. Winner: {manager.winner}")


def main():
    args = parse_args()

    if args.batch > 0:
        run_batch(args)
    elif args.headless:
        asyncio.run(run_single_headless(args))
    else:
        # Varsayılan: Pygame UI modu
        asyncio.run(run_ui(args))


if __name__ == "__main__":
    main()
