"""
response_parser.py — LLM JSON yanıtı parse ve Pydantic validation
"""
from __future__ import annotations
import json
import re
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


VALID_ACTIONS = {
    "ATTACK", "DEFEND", "EXPAND", "ECONOMY", "RESEARCH",
    "TRADE", "DIPLOMACY", "BUILD", "RECRUIT", "MOVE_ARMY", "DISPATCH_ARMY"
}
VALID_DIPLOMACY_SUBACTIONS = {"PEACE", "TRADE", "ALLIANCE", "WAR"}
VALID_BUILDINGS = {"FARM", "LUMBER_MILL", "MINE", "FORT", "ROAD", "CITY"}


VALID_UNITS = {
    "INFANTRY", "ARCHER", "CAVALRY", "CATAPULT", "SPEARMAN", "BOWMAN",
    "HORSEMAN", "MAGE", "SWORDSMAN", "FIGHTER", "SCOUT", "SHAMAN", "GRUNT", "WARRIOR"
}


class AIDecision(BaseModel):
    """AI yanıtının doğrulanmış modeli."""
    action: str
    target: Optional[str] = None
    sub_action: Optional[str] = None
    diplomatic_message: Optional[str] = None
    army_id: Optional[str] = None
    dest_x: Optional[int] = None
    dest_y: Optional[int] = None
    split_amount: Optional[int] = None
    reason: Optional[str] = None
    thought: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_thought_and_reason(cls, data):
        if isinstance(data, dict):
            if "thought" in data and not data.get("reason"):
                data["reason"] = data["thought"]
            elif "reason" in data and not data.get("thought"):
                data["thought"] = data["reason"]
        return data

    @field_validator("diplomatic_message")
    @classmethod
    def validate_diplomatic_message(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "null" or v == "":
            return None
        return v.strip()

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in VALID_ACTIONS:
            return "DEFEND"
        return v

    @field_validator("sub_action")
    @classmethod
    def validate_sub_action(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "null":
            return None
        v = v.upper().strip()
        valid_all_subs = VALID_DIPLOMACY_SUBACTIONS | VALID_BUILDINGS | VALID_UNITS
        if v not in valid_all_subs:
            return v
        return v

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "null" or v == "":
            return None
        return v.strip()


class ParseResult:
    def __init__(
        self,
        decision: Optional[AIDecision],
        raw_response: str,
        error: Optional[str] = None,
        used_fallback: bool = False,
    ):
        self.decision = decision
        self.raw_response = raw_response
        self.error = error
        self.used_fallback = used_fallback
        self.is_valid = decision is not None and not used_fallback

    def __repr__(self) -> str:
        if self.is_valid:
            return f"ParseResult(OK: {self.decision.action})"
        return f"ParseResult(FALLBACK, error={self.error})"


class ResponseParser:
    """LLM'den gelen ham string'i parse eder ve doğrular."""

    FALLBACK_DECISION = AIDecision(action="DEFEND", target=None, reason="Fallback: parse error")

    def parse(self, raw_response: str) -> ParseResult:
        """
        1. JSON'u bul ve parse et
        2. Pydantic ile validate et
        3. Başarısız olursa fallback döndür
        """
        # JSON bloğunu bul
        json_str = self._extract_json(raw_response)
        if not json_str:
            return ParseResult(
                decision=self.FALLBACK_DECISION,
                raw_response=raw_response,
                error="No JSON found in response",
                used_fallback=True,
            )

        # Parse et
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return ParseResult(
                decision=self.FALLBACK_DECISION,
                raw_response=raw_response,
                error=f"JSON decode error: {e}",
                used_fallback=True,
            )

        # Pydantic validation
        try:
            decision = AIDecision(**data)
            return ParseResult(decision=decision, raw_response=raw_response)
        except Exception as e:
            return ParseResult(
                decision=self.FALLBACK_DECISION,
                raw_response=raw_response,
                error=f"Validation error: {e}",
                used_fallback=True,
            )

    def _extract_json(self, text: str) -> Optional[str]:
        """Yanıttan JSON bloğunu çıkar."""
        # Kod bloğu içindeyse temizle
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        # Tam JSON bloğu bul
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            return match.group()
        return None
