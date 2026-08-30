"""
view_model.py — Read-only rendering view of the simulation.

The renderer uses this adapter to READ simulation state without reaching
into TurnManager internals directly. It exposes no setters, so rendering
code cannot mutate simulation state through it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.turn_manager import TurnManager


class ViewModel:
    """Read-only projection of a TurnManager for rendering purposes."""

    def __init__(self, manager: "TurnManager"):
        self._manager = manager

    @property
    def game_map(self):
        return self._manager.game_map

    @property
    def countries(self):
        return self._manager.countries

    @property
    def diplomacy(self):
        return self._manager.diplomacy

    @property
    def events(self):
        return self._manager.events

    @property
    def entities(self):
        return self._manager.entities

    @property
    def current_turn(self) -> int:
        return self._manager.current_turn

    @property
    def max_turns(self) -> int:
        return self._manager.max_turns

    @property
    def winner(self):
        return self._manager.winner

    @property
    def win_reason(self):
        return self._manager.win_reason

    @property
    def is_paused(self) -> bool:
        return self._manager.is_paused

    @property
    def speed_multiplier(self) -> float:
        return self._manager.speed_multiplier

    @property
    def latest_decision(self) -> Optional[dict]:
        return getattr(self._manager, "latest_decision", None)
