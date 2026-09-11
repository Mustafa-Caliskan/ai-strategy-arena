"""
backend/game/engine.py
3 Oyunculu Tur Motoru: İkili Diplomasi, 6 Yönlü Elçi Makinesi & Kaynak Yönetimi
"""
from __future__ import annotations
import random
from typing import Optional, Dict, Any, List

from .state import (
    GameState, SideState, DiplomaticStatus,
    EnvoyState, EnvoyPhase, BilateralRelation
)

TECH_COSTS = {
    "military": [35, 75, 130, 220],
    "economic": [30, 70, 130, 220],
    "naval":    [30, 70, 120, 200],
}

RECRUIT_COSTS = {
    "WORKER":   10,
    "INFANTRY": 16,
    "ARCHER":   16,
    "CAVALRY":  20,
    "MAGE":     20,
    "HEAVY":    20,
    "SIEGE":    45,
    "TROLL":    40,
    "DRAGON":  120,
    "SPY":      18,
    "SHIP":     30,
    "PIRATE":   30,
    "GOBLIN":   10,
}

BUILD_COSTS = {
    "FARM":     {"gold": 25, "wood": 20, "stone": 0},
    "MINE":     {"gold": 35, "wood": 25, "stone": 0},
    "BARRACKS": {"gold": 30, "wood": 30, "stone": 20},
    "FORT":     {"gold": 40, "wood": 0,  "stone": 40},
    "PORT":     {"gold": 50, "wood": 40, "stone": 0},
}

BUILD_CAPS = {
    "FARM":     3,
    "MINE":     3,
    "BARRACKS": 2,
    "FORT":     2,
    "PORT":     1,
}


class GameEngine:
    def __init__(self, state: GameState):
        self.state = state

    # ──────────────────────────────────────────
    # TUR BAŞI SAYAÇLARI
    # ──────────────────────────────────────────
    def advance_turn_counters(self) -> list[dict]:
        gs = self.state
        events = []

        # 1. İlk Temas
        if not gs.first_contact_made and gs.turn >= 3:
            gs.first_contact_made = True
            events.append({"type": "FIRST_CONTACT"})

        # 2. İkili Diplomatik İlişki Sayaçları
        for rel_key, rel in gs.relations.items():
            if rel.pact_turns > 0:
                rel.pact_turns -= 1
                if rel.pact_turns == 0 and rel.status != DiplomaticStatus.WAR:
                    rel.status = DiplomaticStatus.NEUTRAL
                    events.append({"type": "PACT_EXPIRED", "pair": rel_key})

            if rel.war_turns > 0:
                rel.war_turns -= 1
                if rel.war_turns == 0:
                    rel.status = DiplomaticStatus.NEUTRAL
                    events.append({"type": "WAR_ENDED", "pair": rel_key})

        # 3. 6 Yönlü Elçi İlerlemesi
        for key, envoy in gs.envoys.items():
            envoy_events = self._advance_envoy(key, envoy)
            events.extend(envoy_events)

        return events

    def _advance_envoy(self, key: str, envoy: EnvoyState) -> list[dict]:
        gs = self.state
        t = gs.turn
        events = []
        if envoy.phase == EnvoyPhase.IDLE:
            return []

        src_side_id  = envoy.from_side
        dest_side_id = envoy.to_side

        if envoy.phase == EnvoyPhase.DEPARTURE and t >= envoy.arrives_turn:
            envoy.phase = EnvoyPhase.ARRIVAL
            dest_side = gs.sides.get(dest_side_id)
            src_side  = gs.sides.get(src_side_id)
            if dest_side and src_side:
                dest_side.inbox_letters.append({
                    "from_id": src_side_id,
                    "from_name": src_side.name,
                    "proposal": envoy.proposal,
                    "message": envoy.message
                })
            events.append({
                "type":     "ENVOY_ARRIVE",
                "from_id":  src_side_id,
                "to_id":    dest_side_id,
                "proposal": envoy.proposal,
                "message":  envoy.message,
            })

        elif envoy.phase == EnvoyPhase.ARRIVAL and t >= envoy.returns_turn:
            envoy.phase = EnvoyPhase.RETURN
            events.append({
                "type":    "ENVOY_RETURN",
                "from_id": src_side_id,
                "to_id":   dest_side_id,
            })

        elif envoy.phase == EnvoyPhase.RETURN and t > envoy.done_turn:
            envoy.phase = EnvoyPhase.DONE
            src_side = gs.sides.get(src_side_id)
            if src_side:
                src_side.has_active_envoy = False
            gs.envoys[key] = EnvoyState()
            events.append({
                "type":    "ENVOY_DONE",
                "from_id": src_side_id,
            })

        return events

    # ──────────────────────────────────────────
    # KARAR UYGULAMA (SIDE 1, 2 VEYA 3)
    # ──────────────────────────────────────────
    def apply_orders(self, side_id: int, orders: dict) -> list[dict]:
        gs = self.state
        side = gs.sides[side_id]
        events = []

        # 1. Diplomasi
        dip_events = self._apply_diplomacy(side_id, orders.get("diplomacy"))
        events.extend(dip_events)

        # 2. Eylemler
        for act in orders.get("actions", []):
            act_events = self._apply_action(side_id, act)
            events.extend(act_events)

        # 3. Kaynak Üretimi
        income = self._produce_resources(side_id)
        events.append({
            "type":    "INCOME",
            "side_id": side_id,
            "amount":  income,
            "gold":    side.resources.gold,
            "wood":    side.resources.wood,
            "stone":   side.resources.stone,
        })

        return events

    def _resolve_target_id(self, side_id: int, target_raw: Any) -> Optional[int]:
        if not target_raw:
            # Varsayılan diğer rakiplerden ilki
            candidates = [s for s in (1, 2, 3) if s != side_id]
            return candidates[0] if candidates else None

        t_str = str(target_raw).upper()
        if "OPENAI" in t_str or t_str == "1" or t_str == "AI_A":
            return 1 if side_id != 1 else 2
        elif "DEEPSEEK" in t_str or t_str == "2" or t_str == "AI_B":
            return 2 if side_id != 2 else 1
        elif "CLAUDE" in t_str or "ANTHROPIC" in t_str or t_str == "3" or t_str == "AI_C":
            return 3 if side_id != 3 else 1
        return None

    def _apply_diplomacy(self, side_id: int, dip: Optional[dict]) -> list[dict]:
        if not dip:
            return []
        gs = self.state
        side = gs.sides[side_id]
        events = []

        proposal = (dip.get("proposal") or "").upper()
        message  = (dip.get("message") or "").strip()
        target_id = self._resolve_target_id(side_id, dip.get("target"))

        if not proposal or proposal == "NULL" or not target_id or target_id == side_id:
            return []

        rel = gs.get_relation(side_id, target_id)

        # Mevcut pakt varken tekrar pakt teklif yasağı
        if proposal == "OFFER_NON_AGGRESSION" and rel.pact_turns > 0:
            return []

        # Elçi gönder
        if proposal not in ("ACCEPT_PROPOSAL", "REJECT_PROPOSAL") and message and not side.has_active_envoy:
            envoy_key = f"{side_id}_to_{target_id}"
            envoy = EnvoyState(
                phase=EnvoyPhase.DEPARTURE,
                from_side=side_id,
                to_side=target_id,
                proposal=proposal,
                message=message,
                departure_turn=gs.turn,
                arrives_turn=gs.turn + 1,
                returns_turn=gs.turn + 2,
                done_turn=gs.turn + 3,
            )
            gs.envoys[envoy_key] = envoy
            side.has_active_envoy = True
            events.append({
                "type":     "ENVOY_DEPART",
                "from_id":  side_id,
                "to_id":    target_id,
                "proposal": proposal,
                "message":  message,
            })

        # Diplomatik durum güncellemeleri
        other = gs.sides.get(target_id)
        if proposal == "BETRAY_ATTACK":
            side.betrayals += 1
            rel.status = DiplomaticStatus.WAR
            rel.war_turns = 5
            rel.pact_turns = 0
            events.append({"type": "BETRAY_ATTACK", "from_id": side_id, "to_id": target_id})

        elif proposal == "DECLARE_WAR":
            rel.status = DiplomaticStatus.WAR
            rel.war_turns = 5
            rel.pact_turns = 0
            events.append({"type": "WAR_DECLARED", "from_id": side_id, "to_id": target_id})

        elif proposal == "OFFER_ALLIANCE":
            rel.status = DiplomaticStatus.ALLIANCE
            rel.pact_turns = 6
            events.append({"type": "ALLIANCE_FORMED", "pair": f"{side_id}_{target_id}"})

        elif proposal == "OFFER_NON_AGGRESSION":
            rel.status = DiplomaticStatus.NON_AGGRESSION
            rel.pact_turns = 5
            events.append({"type": "PACT_FORMED", "pair": f"{side_id}_{target_id}"})

        elif proposal == "OFFER_TRADE" and other:
            side.income_bonus += 10
            side.income_bonus_turns = 4
            other.income_bonus += 10
            other.income_bonus_turns = 4
            events.append({"type": "TRADE_PACT", "pair": f"{side_id}_{target_id}"})

        elif proposal == "SEND_MISLEADING_LETTER":
            side.fake_letters += 1
            events.append({"type": "FAKE_LETTER", "from_id": side_id, "to_id": target_id})

        return events

    def _apply_action(self, side_id: int, act: dict) -> list[dict]:
        gs = self.state
        side = gs.sides[side_id]
        events = []
        act_type = (act.get("type") or "").upper()
        side.unique_actions.add(act_type)

        if act_type == "RECRUIT":
            unit = (act.get("unit") or "INFANTRY").upper()
            events.extend(self._recruit(side_id, unit))

        elif act_type == "BUILD":
            building = (act.get("building") or "FARM").upper()
            events.extend(self._build(side_id, building))

        elif act_type == "RESEARCH":
            tree = (act.get("tree") or "").lower()
            events.extend(self._research(side_id, tree))

        elif act_type == "ORDER_ARMY":
            stance = (act.get("stance") or "").upper()
            target_raw = act.get("target")
            events.extend(self._order_army(side_id, stance, target_raw))

        return events

    def _recruit(self, side_id: int, unit: str) -> list[dict]:
        side = self.state.sides[side_id]
        events = []
        cost = RECRUIT_COSTS.get(unit, 16)

        if unit == "WORKER":
            if side.workers >= 4:
                if side.resources.gold >= 16:
                    side.resources.gold -= 16
                    side.units += 1
                    events.append({"type": "RECRUIT", "side_id": side_id, "unit": "INFANTRY", "note": "worker_cap"})
            elif side.resources.gold >= cost:
                side.resources.gold -= cost
                side.workers += 1
                events.append({"type": "RECRUIT", "side_id": side_id, "unit": "WORKER", "workers": side.workers})
        elif unit == "SPY":
            if side.spies < 2 and side.resources.gold >= cost:
                side.resources.gold -= cost
                side.spies += 1
                events.append({"type": "RECRUIT", "side_id": side_id, "unit": "SPY", "spies": side.spies})
        elif unit in ("SHIP", "PIRATE"):
            if side.ships < 8 and side.resources.gold >= cost:
                side.resources.gold -= cost
                side.ships += 1
                events.append({"type": "RECRUIT", "side_id": side_id, "unit": unit, "ships": side.ships})
        else:
            if side.units < 25 and side.resources.gold >= cost:
                side.resources.gold -= cost
                side.units += 1
                events.append({"type": "RECRUIT", "side_id": side_id, "unit": unit, "units": side.units})

        return events

    def _build(self, side_id: int, building: str) -> list[dict]:
        side = self.state.sides[side_id]
        costs = BUILD_COSTS.get(building)
        cap   = BUILD_CAPS.get(building, 99)
        if not costs:
            return []

        b = side.buildings
        counts = {
            "FARM": b.farms, "MINE": b.mines, "BARRACKS": b.barracks,
            "FORT": b.forts, "PORT": b.ports
        }
        if counts.get(building, 0) >= cap:
            return []
        if (side.resources.gold < costs["gold"] or side.resources.wood < costs["wood"] or side.resources.stone < costs["stone"]):
            return []

        side.resources.gold  -= costs["gold"]
        side.resources.wood  -= costs["wood"]
        side.resources.stone -= costs["stone"]

        if building == "FARM":       b.farms += 1
        elif building == "MINE":     b.mines += 1
        elif building == "BARRACKS": b.barracks += 1
        elif building == "FORT":     b.forts += 1
        elif building == "PORT":     b.ports += 1

        return [{"type": "BUILD", "side_id": side_id, "building": building}]

    def _research(self, side_id: int, tree: str) -> list[dict]:
        side = self.state.sides[side_id]
        if tree not in ("military", "economic", "naval"):
            return []
        lvl = getattr(side.tech, tree, 0)
        costs = TECH_COSTS.get(tree, [])
        if lvl >= len(costs):
            return []
        cost = costs[lvl]
        if side.resources.gold < cost:
            return []

        side.resources.gold -= cost
        setattr(side.tech, tree, lvl + 1)
        return [{"type": "RESEARCH", "side_id": side_id, "tree": tree, "level": lvl + 1}]

    def _order_army(self, side_id: int, stance: str, target_raw: Any = None) -> list[dict]:
        gs = self.state
        side = gs.sides[side_id]
        events = []

        if "ATTACK" in stance or "CONQUER" in stance:
            side.attacks += 1
            target_id = self._resolve_target_id(side_id, target_raw or stance)
            if target_id and target_id != side_id and gs.turn >= 3:
                rel = gs.get_relation(side_id, target_id)
                rel.status = DiplomaticStatus.WAR
                rel.war_turns = max(rel.war_turns, 5)
                rel.pact_turns = 0
                events.append({"type": "WAR_TRIGGERED", "from_id": side_id, "to_id": target_id, "stance": stance})

        if stance == "CONQUER_ISLAND" and gs.turn >= 3:
            gs.island_controller_id = side_id
            events.append({"type": "ISLAND_CAPTURED", "side_id": side_id})

        elif stance in ("EAST_TRADE_ROUTE", "NAVAL_PATROL"):
            if side.ships > 0:
                side.trade_ships = min(side.ships, side.trade_ships + 1)
                events.append({"type": "TRADE_ROUTE", "side_id": side_id})

        elif stance == "RAID_BARBARIANS":
            if side.barbarian_villages < 5 and random.random() < 0.65:
                side.barbarian_villages += 1
                events.append({"type": "BARBARIAN_RAIDED", "side_id": side_id, "villages": side.barbarian_villages})

        events.append({"type": "ARMY_ORDER", "side_id": side_id, "stance": stance})
        return events

    def _produce_resources(self, side_id: int) -> int:
        gs   = self.state
        side = gs.sides[side_id]

        side.resources.wood  += side.workers * 10
        side.resources.stone += side.workers * 8

        income = side.compute_income(
            world_event=gs.active_world_event,
            island_owner_id=gs.island_controller_id,
        )
        side.resources.gold += income

        if side.income_bonus_turns > 0:
            side.income_bonus_turns -= 1
            if side.income_bonus_turns == 0:
                side.income_bonus = 0

        return income
