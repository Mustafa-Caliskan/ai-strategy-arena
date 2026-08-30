"""
turn_manager.py — Ana oyun döngüsü
Game State → AI Call → Validate → Execute → World Update → Next Turn
"""
from __future__ import annotations
import asyncio
import logging
import random
from typing import Optional, TYPE_CHECKING

from ai.action_validator import ActionValidator
from ai.prompt_builder import PromptBuilder
from ai.response_parser import ResponseParser
from game.combat import CombatSystem
from game.diplomacy import DiplomacySystem
from game.economy import EconomySystem
from game.entities import EntityManager
from game.game_state import GameStateBuilder, WinConditionChecker
from simulation.event_system import EventSystem

if TYPE_CHECKING:
    from ai.base_provider import AIProvider
    from game.country import Country
    from game.map import GameMap


logger = logging.getLogger(__name__)

MAX_API_RETRIES = 3


class TurnManager:
    """
    Oyun tur döngüsünü yönetir.
    Tüm sistemleri koordine eder.
    """

    def __init__(
        self,
        countries: list["Country"],
        providers: dict[str, "AIProvider"],  # agent_id → provider
        game_map: "GameMap",
        max_turns: int = 200,
        seed: Optional[int] = None,
        log_dir: str = "logs/decisions",
    ):
        self.countries = countries
        self.providers = providers
        self.game_map = game_map
        self.max_turns = max_turns
        self.current_turn = 0
        self._rng = random.Random(seed)

        # Sistemler
        self.diplomacy = DiplomacySystem([c.agent_id for c in countries])
        self.economy = EconomySystem()
        self.combat = CombatSystem()
        self.entities = EntityManager()
        self.state_builder = GameStateBuilder()
        self.win_checker = WinConditionChecker()
        self.prompt_builder = PromptBuilder()
        self.parser = ResponseParser()
        self.validator = ActionValidator()
        self.events = EventSystem(log_dir=log_dir)

        # İlk toprak sayımı
        self.win_checker.update_territory_counts(countries, game_map)

        # Durum
        self.winner: Optional[str] = None
        self.win_reason: Optional[str] = None
        self.is_running = False
        self.is_paused = False
        self.speed_multiplier = 1.0   # UI tarafından ayarlanır
        self.telemetry_history: list[dict] = []
        self.latest_decision: Optional[dict] = None

    def get_active_countries(self) -> list["Country"]:
        return [c for c in self.countries if c.is_active()]

    async def run_game_async(
        self, on_turn_complete=None
    ) -> tuple[Optional[str], str]:
        """
        Oyunu asenkron olarak çalıştır.
        on_turn_complete(turn_manager): her tur sonrası çağrılır (UI güncelleme için).
        """
        self.is_running = True
        logger.info(f"Game started. Max turns: {self.max_turns}")

        while self.current_turn < self.max_turns:
            if not self.is_running:
                break

            # Pause bekleme
            while self.is_paused:
                await asyncio.sleep(0.1)
                if not self.is_running:
                    break

            self.current_turn += 1
            await self._process_turn()

            # Kazanma kontrolü
            result = self.win_checker.check(
                self.countries, self.current_turn, self.max_turns
            )
            if result:
                self.winner, self.win_reason = result
                self.events.add_narrative(
                    self.current_turn,
                    f"GAME OVER: {self.winner} wins by {self.win_reason}!"
                )
                break

            # UI callback
            if on_turn_complete:
                on_turn_complete(self)

            # Speed control
            delay = max(0.05, 1.0 / self.speed_multiplier)
            await asyncio.sleep(delay)

        self.is_running = False
        logger.info(f"Game ended. Winner: {self.winner}, Reason: {self.win_reason}")
        return self.winner, self.win_reason or "max_turns"

    def run_game_sync(self) -> tuple[Optional[str], str]:
        """Headless/batch mod için sync çalıştırıcı."""
        return asyncio.run(self.run_game_async())

    async def _process_turn(self) -> None:
        """Tek bir turu işle."""
        turn = self.current_turn
        logger.debug(f"--- Turn {turn} ---")

        active = self.get_active_countries()

        # 0. Fiziksel varlıkların hareketi, çatışmalar ve teslimatlar
        self.entities.step_all(self.game_map, turn, self.events, self.countries, self.combat)

        # 1. Haydutlar (BANDITS) Otomatik Saldırı Döngüsü
        bandit_c = next((c for c in active if c.agent_id == "BANDITS"), None)
        if bandit_c and bandit_c.is_active():
            self._process_bandit_turn(bandit_c, active, turn)

        # 2. Her AI kararını al ve uygula
        for country in active:
            if not country.is_active() or country.agent_id == "BANDITS":
                continue

            provider = self.providers.get(country.agent_id)
            if not provider:
                logger.warning(f"No provider for {country.agent_id}")
                continue

            await self._process_agent_turn(country, provider, active, turn)

        # 3. Ekonomi güncellemesi (tüm aktif ülkeler)
        for country in self.get_active_countries():
            result = self.economy.process_turn(country, self.game_map)
            for ev in result.events:
                self.events.add_narrative(turn, ev)

        # 4. Toprak sayımını güncelle
        self.win_checker.update_territory_counts(self.countries, self.game_map)

        # 5. Diplomasi ve Paktlar tick
        pact_events = self.diplomacy.tick_all(turn)
        for pe in pact_events:
            self.events.add_narrative(turn, pe)

        # 6. Hayatta kalma sayacı
        for country in self.get_active_countries():
            country.turns_survived += 1

    def _process_bandit_turn(self, bandits: "Country", active_countries: list["Country"], turn: int) -> None:
        """Kara Sancaklı Haydutların otomatik saldırı ve yağma döngüsü."""
        import math
        from game.entities import UnitClass, ArmyStatus

        bandit_armies = [a for a in self.entities.armies.values() if a.is_alive() and a.owner == "BANDITS"]

        # 1. Birlik sayısı az ise yeni haydut alayı bas
        if len(bandit_armies) < 2 and bandits.resources.army >= 20:
            unit_cls = UnitClass.CAVALRY if (turn % 2 == 0) else UnitClass.INFANTRY
            self.entities.spawn_army("BANDITS", bandits.capital_x, bandits.capital_y, size=25, unit_class=unit_cls, turn=turn)
            bandits.resources.army -= 20
            self.events.add_narrative(turn, f"💀 [BANDIT_RAID] Kara Sancaklı Haydutlar ({unit_cls.value.upper()}) vadiden taarruza geçti!")

        # 2. En yakın medeniyete doğrudan taarruz et
        target_countries = [c for c in active_countries if c.agent_id != "BANDITS"]
        if not target_countries:
            return

        for army in bandit_armies:
            if army.status != ArmyStatus.ENGAGED:
                # Hedef olarak başkenti en yakın ülkeyi seç (OpenAI veya DeepSeek)
                closest_c = min(target_countries, key=lambda c: math.hypot(army.x - c.capital_x, army.y - c.capital_y))
                self.entities.move_army_towards(army.id, closest_c.capital_x, closest_c.capital_y, self.game_map)

    async def _process_agent_turn(
        self,
        country: "Country",
        provider: "AIProvider",
        active_countries: list["Country"],
        turn: int,
    ) -> None:
        """Bir AI agent'ının kararını al ve uygula."""
        import time
        # Game state oluştur (fog of war ile)
        state = self.state_builder.build(
            turn=turn,
            perspective_agent=country,
            all_countries=active_countries,
            game_map=self.game_map,
            diplomacy=self.diplomacy,
            max_turns=self.max_turns,
        )
        state_hash = self.state_builder.build_hash(state)

        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(state)

        # API çağrısı (retry mekanizması)
        raw_response = None
        api_error = None
        start_time = time.perf_counter()
        for attempt in range(1, MAX_API_RETRIES + 1):
            try:
                self.events.add_narrative(turn, f"{country.agent_id} is thinking...")
                raw_response = await provider.decide_async(system_prompt, user_prompt)
                break
            except Exception as e:
                api_error = str(e)
                logger.warning(f"API attempt {attempt}/{MAX_API_RETRIES} failed for {country.agent_id}: {e}")
                if attempt < MAX_API_RETRIES:
                    await asyncio.sleep(1.0 * attempt)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if raw_response is None:
            # Tüm retry'lar başarısız: fallback
            provider._fallback_count += 1
            self.events.record(
                turn=turn,
                agent_id=country.agent_id,
                action="DEFEND",
                result="API failed, fallback DEFEND",
                game_state_hash=state_hash,
                used_fallback=True,
                parse_error=api_error,
            )
            self._execute_action("DEFEND", country, active_countries, turn)
            return

        # Parse
        parse_result = self.parser.parse(raw_response)

        # Validate
        decision = parse_result.decision
        validation = self.validator.validate(
            decision, country, active_countries, self.game_map, self.diplomacy
        )

        if not validation.is_valid:
            logger.warning(
                f"{country.agent_id} action {decision.action} rejected: {validation.reason}"
            )
            # Fallback action uygula
            effective_action = validation.action
            self.events.record(
                turn=turn,
                agent_id=country.agent_id,
                action=effective_action,
                result=f"Rejected ({validation.reason}), fallback: {effective_action}",
                game_state_hash=state_hash,
                used_fallback=True,
                parse_error=validation.reason,
            )
        else:
            effective_action = validation.action

        # Execute
        result_msg = self._execute_action(
            effective_action,
            country,
            active_countries,
            turn,
            target_id=validation.target,
            sub_action=validation.sub_action,
        )

        # Diplomatik elçi mesajı varsa fiziksel elçi yola çıkar (Aynı anda en fazla 1 aktif elçi)
        diplomatic_msg = decision.diplomatic_message if hasattr(decision, "diplomatic_message") else None
        target_id_for_msg = validation.target or decision.target
        active_envoys = [e for e in self.entities.envoys.values() if e.owner == country.agent_id and e.status.value == "traveling"]

        if diplomatic_msg and target_id_for_msg and len(active_envoys) == 0:
            target_country = self._find_country(target_id_for_msg, self.countries)
            if target_country and target_country.agent_id != country.agent_id:
                envoy = self.entities.dispatch_envoy(
                    country.agent_id,
                    target_country.agent_id,
                    country.capital_x,
                    country.capital_y,
                    target_country.capital_x,
                    target_country.capital_y,
                    diplomatic_msg,
                    None,
                    turn,
                    self.game_map,
                )
                self.events.add_narrative(
                    turn,
                    f"🐎 [ENVOY_CREATED] Envoy {envoy.id} dispatched from {country.agent_id} capital towards {target_country.agent_id}"
                )
                country.total_messages_sent += 1

        thought_str = getattr(decision, "thought", None) or getattr(decision, "reasoning", "") or f"{country.agent_id} ordered {effective_action} {validation.sub_action or ''} towards {validation.target or 'frontlines'}."

        # Telemetry kaydet (Web Dashboard Inspector için)
        telemetry_entry = {
            "turn": turn,
            "agent_id": country.agent_id,
            "agent_name": country.name,
            "model": getattr(provider, "model_name", "AI"),
            "latency_ms": round(latency_ms, 1),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_response": raw_response or "{}",
            "action": effective_action,
            "sub_action": validation.sub_action,
            "target": validation.target,
            "thought": thought_str,
            "diplomatic_message": diplomatic_msg,
            "timestamp": time.strftime("%H:%M:%S"),
        }
        self.telemetry_history.append(telemetry_entry)
        if len(self.telemetry_history) > 200:
            self.telemetry_history.pop(0)

        # Kaydet
        self.latest_decision = {
            "agent_id": country.agent_id,
            "action": effective_action,
            "sub_action": validation.sub_action,
            "target": validation.target,
            "result": result_msg,
            "thought": thought_str,
            "diplomatic_message": diplomatic_msg,
            "turn": turn,
        }
        self.events.record(
            turn=turn,
            agent_id=country.agent_id,
            action=effective_action,
            target=validation.target,
            sub_action=validation.sub_action,
            result=result_msg,
            diplomatic_message=diplomatic_msg,
            game_state_hash=state_hash,
            used_fallback=parse_result.used_fallback,
            parse_error=parse_result.error,
        )

    def _execute_action(
        self,
        action: str,
        country: "Country",
        active_countries: list["Country"],
        turn: int,
        target_id: Optional[str] = None,
        sub_action: Optional[str] = None,
    ) -> str:
        """Doğrulanmış eylemi uygula."""
        if action == "ATTACK":
            target = self._find_country(target_id, active_countries)
            if not target:
                return "ATTACK: target not found."
            # Savaş ilan et (zaten yoksa) ve ihlal kontrol et
            if not self.diplomacy.is_at_war(country.agent_id, target_id):
                war_msg = self.diplomacy.apply_declare_war(country, target, turn)
                if "BETRAYAL" in war_msg:
                    self.events.add_narrative(turn, war_msg)
            result = self.combat.resolve_attack(country, target, self.game_map, self._rng)
            country.total_attacks += 1
            target.total_defenses += 1
            for ev in result.events:
                self.events.add_narrative(turn, ev)
            return "; ".join(result.events)

        elif action == "DEFEND":
            return self.combat.resolve_defend(country)

        elif action == "EXPAND":
            return self.combat.resolve_expand(country, self.game_map, self._rng)

        elif action == "ECONOMY":
            return self.economy.apply_economy_action(country)

        elif action == "RESEARCH":
            return self.economy.apply_research_action(country)

        elif action == "BUILD":
            return self.economy.apply_build_action(country, self.game_map, sub_action or "FARM", target_id)

        elif action == "RECRUIT":
            rec_msg = self.economy.apply_recruit_action(country, amount=20)
            if "recruited" in rec_msg.lower():
                from game.entities import UnitClass
                u_class = UnitClass.INFANTRY
                if sub_action:
                    sub_low = sub_action.lower()
                    if "arch" in sub_low:
                        u_class = UnitClass.ARCHER
                    elif "cav" in sub_low or "horse" in sub_low:
                        u_class = UnitClass.CAVALRY
                    elif "cat" in sub_low or "siege" in sub_low:
                        u_class = UnitClass.CATAPULT
                else:
                    existing = self.entities.get_armies_for(country.agent_id)
                    classes = [UnitClass.INFANTRY, UnitClass.ARCHER, UnitClass.CAVALRY, UnitClass.INFANTRY, UnitClass.ARCHER, UnitClass.CATAPULT]
                    u_class = classes[len(existing) % len(classes)]

                army_unit = self.entities.spawn_army(
                    country.agent_id, country.capital_x, country.capital_y, size=20, unit_class=u_class, turn=turn
                )
                target = next((c for c in active_countries if c.agent_id != country.agent_id), None)
                if target:
                    army_unit.set_target(target.capital_x, target.capital_y, self.game_map)

                icon = {"infantry": "🛡️", "archer": "🏹", "cavalry": "🐎", "catapult": "☄️"}.get(u_class.value, "⚔️")
                self.events.add_narrative(
                    turn,
                    f"{icon} [RECRUIT] {army_unit.id} ({u_class.value.upper()}) formed at ({country.capital_x},{country.capital_y}) and marching forward!"
                )
            return rec_msg

        elif action == "TRADE":
            target = self._find_country(target_id, active_countries)
            if not target:
                return "TRADE: target not found."
            return self.diplomacy.apply_trade(country, target)

        elif action == "DIPLOMACY":
            target = self._find_country(target_id, active_countries)
            if not target:
                return "DIPLOMACY: target not found."
            return self.diplomacy.apply_diplomacy_action(country, target, sub_action or "PEACE", turn)

        elif action == "MOVE_ARMY":
            armies = self.entities.get_armies_for(country.agent_id)
            if not armies:
                return f"{country.agent_id} MOVE_ARMY: No field armies available."
            army = armies[0]
            target = self._find_country(target_id, active_countries)
            dest_x = target.capital_x if target else country.capital_x
            dest_y = target.capital_y if target else country.capital_y
            army.set_target(dest_x, dest_y, self.game_map)
            return f"{country.agent_id} ordered {army.id} to march towards ({dest_x},{dest_y})."

        elif action == "DISPATCH_ARMY":
            split_size = min(30, max(10, country.garrison_army // 2))
            if country.garrison_army < split_size:
                return f"{country.agent_id} DISPATCH_ARMY: Insufficient garrison ({country.garrison_army})."
            country.garrison_army -= split_size
            army = self.entities.spawn_army(
                country.agent_id, country.capital_x, country.capital_y, size=split_size, turn=turn
            )
            target = self._find_country(target_id, active_countries)
            if target:
                army.set_target(target.capital_x, target.capital_y, self.game_map)
            return f"{country.agent_id} dispatched {army.id} [Size: {split_size}] towards {target_id or 'border'}."

        return f"Unknown action: {action}"

    def _find_country(
        self, agent_id: Optional[str], countries: list["Country"]
    ) -> Optional["Country"]:
        if not agent_id:
            return None
        for c in countries:
            if c.agent_id == agent_id:
                return c
        return None

    def get_status_summary(self) -> dict:
        """UI ve headless mod için anlık durum özeti."""
        return {
            "turn": self.current_turn,
            "max_turns": self.max_turns,
            "is_running": self.is_running,
            "winner": self.winner,
            "win_reason": self.win_reason,
            "countries": [c.to_dict() for c in self.countries],
            "diplomacy": self.diplomacy.get_all_relations_dict(),
            "action_stats": self.events.get_action_stats(),
        }
