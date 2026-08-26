"""
action_validator.py — Oyun kuralı doğrulaması
AI kararı JSON parse'dan geçtikten sonra burada oyun kurallarına göre kontrol edilir.
LLM oyun kurallarını değiştiremez.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ai.response_parser import AIDecision

if TYPE_CHECKING:
    from game.country import Country
    from game.map import GameMap
    from game.diplomacy import DiplomacySystem


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str
    action: str
    target: Optional[str] = None
    sub_action: Optional[str] = None


class ActionValidator:
    """
    AI kararını oyun kurallarına karşı doğrular.
    Geçersiz kararlar reddedilir, fallback uygulanır.
    """

    def validate(
        self,
        decision: AIDecision,
        country: "Country",
        all_countries: list["Country"],
        game_map: "GameMap",
        diplomacy: "DiplomacySystem",
    ) -> ValidationResult:
        """
        Kararı doğrula. ValidationResult döndür.
        """
        action = decision.action
        target_id = decision.target
        sub_action = decision.sub_action

        r = country.resources
        active_others = {
            c.agent_id: c for c in all_countries
            if c.agent_id != country.agent_id and c.is_active()
        }

        # ── ATTACK ──────────────────────────────────────────────────
        if action == "ATTACK":
            if not target_id:
                return self._fail("ATTACK requires a target.", "DEFEND")
            if target_id not in active_others:
                return self._fail(
                    f"ATTACK target '{target_id}' does not exist or is eliminated.",
                    "DEFEND"
                )
            if r.army <= 0:
                return self._fail("ATTACK failed: no army.", "DEFEND")
            # Savaş gerektirmez — ATTACK savaş ilan da eder
            return ValidationResult(True, "OK", "ATTACK", target_id)

        # ── DEFEND ──────────────────────────────────────────────────
        elif action == "DEFEND":
            return ValidationResult(True, "OK", "DEFEND")

        # ── EXPAND ──────────────────────────────────────────────────
        elif action == "EXPAND":
            adj = game_map.get_adjacent_unowned(country.agent_id)
            if not adj:
                return self._fail("EXPAND: no adjacent unclaimed territory.", "DEFEND")
            if r.gold < 40.0:
                return self._fail(f"EXPAND: insufficient gold ({r.gold:.0f}/40).", "DEFEND")
            return ValidationResult(True, "OK", "EXPAND")

        # ── ECONOMY ─────────────────────────────────────────────────
        elif action == "ECONOMY":
            if r.gold < 60.0:
                return self._fail(f"ECONOMY: insufficient gold ({r.gold:.0f}/60).", "DEFEND")
            return ValidationResult(True, "OK", "ECONOMY")

        # ── RESEARCH ────────────────────────────────────────────────
        elif action == "RESEARCH":
            cost = 120.0 + r.technology * 40.0
            if r.technology >= r.MAX_TECHNOLOGY:
                return self._fail("RESEARCH: already at max technology.", "ECONOMY")
            if r.gold < cost:
                return self._fail(
                    f"RESEARCH: insufficient gold ({r.gold:.0f}/{cost:.0f}).",
                    "ECONOMY"
                )
            return ValidationResult(True, "OK", "RESEARCH")

        # ── TRADE ───────────────────────────────────────────────────
        elif action == "TRADE":
            if not target_id:
                return self._fail("TRADE requires a target.", "DEFEND")
            if target_id not in active_others:
                return self._fail(f"TRADE target '{target_id}' invalid.", "DEFEND")
            if diplomacy.is_at_war(country.agent_id, target_id):
                return self._fail(f"TRADE: cannot trade with {target_id}, at war.", "DEFEND")
            return ValidationResult(True, "OK", "TRADE", target_id)

        # ── DIPLOMACY ───────────────────────────────────────────────
        elif action == "DIPLOMACY":
            if not target_id:
                return self._fail("DIPLOMACY requires a target.", "DEFEND")
            if target_id not in active_others:
                return self._fail(f"DIPLOMACY target '{target_id}' invalid.", "DEFEND")
            if not sub_action:
                return self._fail("DIPLOMACY requires sub_action (PEACE/TRADE/ALLIANCE/WAR).", "DEFEND")
            valid_sub = {"PEACE", "TRADE", "ALLIANCE", "WAR"}
            if sub_action.upper() not in valid_sub:
                return self._fail(f"DIPLOMACY sub_action '{sub_action}' invalid.", "DEFEND")
            return ValidationResult(True, "OK", "DIPLOMACY", target_id, sub_action.upper())

        # ── BUILD ───────────────────────────────────────────────────
        elif action == "BUILD":
            from game.buildings import BuildingType, BUILDING_COSTS
            valid_buildings = {"FARM", "LUMBER_MILL", "MINE", "FORT", "ROAD", "CITY"}
            if not sub_action or sub_action.upper() not in valid_buildings:
                return self._fail("BUILD requires valid sub_action (FARM/LUMBER_MILL/MINE/FORT/ROAD/CITY).", "ECONOMY")
            
            btype_map = {
                "FARM": BuildingType.FARM,
                "LUMBER_MILL": BuildingType.LUMBER_MILL,
                "MINE": BuildingType.MINE,
                "FORT": BuildingType.FORT,
                "ROAD": BuildingType.ROAD,
                "CITY": BuildingType.CITY,
            }
            btype = btype_map[sub_action.upper()]
            cost = BUILDING_COSTS[btype]
            if r.gold < cost.gold or r.wood < cost.wood or r.stone < cost.stone or r.iron < cost.iron:
                return self._fail(f"BUILD {sub_action} failed: Insufficient resources.", "ECONOMY")
            return ValidationResult(True, "OK", "BUILD", target_id, sub_action.upper())

        # ── RECRUIT ─────────────────────────────────────────────────
        elif action == "RECRUIT":
            if r.gold < 40.0:
                return self._fail(f"RECRUIT failed: Need 40 gold (have {r.gold:.0f}).", "DEFEND")
            if r.iron < 20.0:
                return self._fail(f"RECRUIT failed: Need 20 iron (have {r.iron:.0f}).", "DEFEND")
            if r.army + 20 > r.max_army():
                return self._fail("RECRUIT failed: Population army capacity reached.", "DEFEND")
            return ValidationResult(True, "OK", "RECRUIT")

        # ── MOVE_ARMY ───────────────────────────────────────────────
        elif action == "MOVE_ARMY":
            return ValidationResult(True, "OK", "MOVE_ARMY", target_id)

        # ── DISPATCH_ARMY ───────────────────────────────────────────
        elif action == "DISPATCH_ARMY":
            return ValidationResult(True, "OK", "DISPATCH_ARMY", target_id)

        else:
            return self._fail(f"Unknown action: {action}", "DEFEND")

    def _fail(self, reason: str, fallback_action: str) -> ValidationResult:
        return ValidationResult(
            is_valid=False,
            reason=reason,
            action=fallback_action,
        )
