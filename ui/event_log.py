"""
event_log.py — Grand Strategy Canlı Olay Günlüğü Paneli
"""
from __future__ import annotations
import pygame

COLOR_BG     = (18,  20,  28)
COLOR_PANEL  = (24,  27,  38)
COLOR_BORDER = (48,  54,  76)
COLOR_TEXT   = (215, 220, 230)
COLOR_ATTACK = (245,  95,  95)
COLOR_TRADE  = (255, 210,  65)
COLOR_ALLY   = (110, 180, 255)
COLOR_DIPLOMSG = (225, 155, 255)
COLOR_THINK  = (135, 145, 165)
COLOR_FALLBK = (215, 135,  50)
COLOR_GAME   = (255, 225,  65)


def _classify_color(line: str) -> tuple:
    low = line.lower()
    if "diplomacy msg" in low or "📜" in line or "envoy" in low:
        return COLOR_DIPLOMSG
    if "game over" in low or "winner" in low:
        return COLOR_GAME
    if "attack" in low or "combat" in low or "captured" in low or "war" in low or "clashed" in low or "⚔️" in line:
        return COLOR_ATTACK
    if "trade" in low or "alliance" in low or "pact" in low or "treaty" in low:
        return COLOR_ALLY
    if "thinking" in low:
        return COLOR_THINK
    if "fallback" in low or "rejected" in low:
        return COLOR_FALLBK
    return COLOR_TEXT


class EventLog:
    """Alt panelde kayan modern olay günlüğü."""

    MAX_LINES = 200
    LINE_H    = 18

    def __init__(self, font):
        self.font = font
        self._lines: list[str] = []

    def update(self, new_lines: list[str]) -> None:
        self._lines = new_lines[-self.MAX_LINES:]

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
    ) -> None:
        pygame.draw.rect(surface, COLOR_PANEL, rect)
        pygame.draw.rect(surface, COLOR_BORDER, rect, 1)

        # Başlık ve durum rozeti
        header = self.font.render("CHRONICLE & EVENT LOG", True, (200, 215, 240))
        surface.blit(header, (rect.x + 12, rect.y + 5))

        # Görünür alan
        visible_h = rect.height - 28
        max_visible = visible_h // self.LINE_H

        visible_lines = self._lines[-max_visible:]

        clip = surface.get_clip()
        surface.set_clip(rect)

        y = rect.y + 24
        for line in visible_lines:
            color = _classify_color(line)
            if len(line) > 95:
                line = line[:92] + "..."
            rendered = self.font.render(line, True, color)
            surface.blit(rendered, (rect.x + 12, y))
            y += self.LINE_H

        surface.set_clip(clip)