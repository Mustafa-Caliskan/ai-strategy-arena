"""
event_system.py — Olay üretimi ve JSON decision log
"""
from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class GameEvent:
    turn: int
    agent_id: str
    action: str
    target: str | None
    sub_action: str | None
    result: str
    diplomatic_message: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    game_state_hash: str = ""
    used_fallback: bool = False
    parse_error: str | None = None


class EventSystem:
    """
    Tüm oyun olaylarını kaydeder.
    - İn-memory event log (UI için)
    - JSON decision log (analiz için)
    """

    MAX_DISPLAY_EVENTS = 100     # UI'da gösterilecek max olay sayısı

    def __init__(self, log_dir: str = "logs/decisions"):
        self.events: list[GameEvent] = []
        self.display_log: list[str] = []   # UI event log için string listesi
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = self.log_dir / f"decisions_{self._session_id}.jsonl"

    def record(
        self,
        turn: int,
        agent_id: str,
        action: str,
        target: str | None = None,
        sub_action: str | None = None,
        result: str = "",
        diplomatic_message: str | None = None,
        game_state_hash: str = "",
        used_fallback: bool = False,
        parse_error: str | None = None,
    ) -> GameEvent:
        event = GameEvent(
            turn=turn,
            agent_id=agent_id,
            action=action,
            target=target,
            sub_action=sub_action,
            result=result,
            diplomatic_message=diplomatic_message,
            game_state_hash=game_state_hash,
            used_fallback=used_fallback,
            parse_error=parse_error,
        )
        self.events.append(event)
        self._append_to_file(event)

        # Display log için kısa mesaj
        target_str = f" → {target}" if target else ""
        fallback_str = " [FALLBACK]" if used_fallback else ""
        display = f"[T{turn:03d}] {agent_id}: {action}{target_str}{fallback_str}"
        self.display_log.append(display)
        if len(self.display_log) > self.MAX_DISPLAY_EVENTS:
            self.display_log.pop(0)

        # Eğer diplomatik mesaj varsa log'a ekle
        if diplomatic_message and target:
            msg_display = f"[T{turn:03d}] 📜 [DIPLOMACY MSG] {agent_id} -> {target}: \"{diplomatic_message}\""
            self.display_log.append(msg_display)
            if len(self.display_log) > self.MAX_DISPLAY_EVENTS:
                self.display_log.pop(0)
            logger.info(msg_display)

        logger.info(display)
        return event

    def add_narrative(self, turn: int, message: str) -> None:
        """Savaş/diplomasi sonuçları gibi anlatısal olayları ekle."""
        display = f"[T{turn:03d}] {message}"
        self.display_log.append(display)
        if len(self.display_log) > self.MAX_DISPLAY_EVENTS:
            self.display_log.pop(0)
        logger.info(display)

    def _append_to_file(self, event: GameEvent) -> None:
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "turn": event.turn,
                    "agent": event.agent_id,
                    "action": event.action,
                    "target": event.target,
                    "sub_action": event.sub_action,
                    "diplomatic_message": event.diplomatic_message,
                    "result": event.result,
                    "timestamp": event.timestamp,
                    "game_state_hash": event.game_state_hash,
                    "used_fallback": event.used_fallback,
                    "parse_error": event.parse_error,
                }, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write event log: {e}")

    def get_action_stats(self) -> dict[str, dict[str, int]]:
        """Her AI için action dağılımı istatistiği."""
        stats: dict[str, dict[str, int]] = {}
        for event in self.events:
            if event.agent_id not in stats:
                stats[event.agent_id] = {}
            a = event.action
            stats[event.agent_id][a] = stats[event.agent_id].get(a, 0) + 1
        return stats

    def get_recent_display(self, count: int = 20) -> list[str]:
        return self.display_log[-count:]
