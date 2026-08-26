"""
event_log.py — Scrollable olay günlüğü paneli
"""
from __future__ import annotations
import pygame

COLOR_BG     = (15,  15,  25)
COLOR_BORDER = (50,  50,  80)
COLOR_TEXT   = (200, 200, 210)
COLOR_ATTACK = (220,  80,  80)
COLOR_TRADE  = (255, 200,  50)
COLOR_ALLY   = (100, 160, 255)
COLOR_DIPLOMSG = (215, 140, 255)  # Canlı leylak / mor
COLOR_THINK  = (140, 140, 160)
COLOR_FALLBK = (200, 120,  40)
COLOR_GAME   = (255, 220,  50)


def _classify_color(line: str) -> tuple:
    low = line.lower()
    if "diplomacy msg" in low or "📜" in line:
        return COLOR_DIPLOMSG
    if "game over" in low or "winner" in low:
        return COLOR_GAME
    if "attack" in low or "combat" in low or "captured" in low or "war" in low:
        return COLOR_ATTACK
    if "trade" in low or "alliance" in low:
        return COLOR_ALLY
    if "thinking" in low:
        return COLOR_THINK
    if "fallback" in low or "rejected" in low:
        return COLOR_FALLBK
    return COLOR_TEXT


class EventLog:
    """Alt panelde kayan olay günlüğü."""

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
        pygame.draw.rect(surface, COLOR_BG, rect)
        pygame.draw.rect(surface, COLOR_BORDER, rect, 1)

        # Başlık
        header = self.font.render("EVENT LOG", True, (160, 160, 200))
        surface.blit(header, (rect.x + 8, rect.y + 4))

        # Görünür alan
        visible_h = rect.height - 28
        max_visible = visible_h // self.LINE_H

        # En son olayları göster (yukarıdan aşağı, en yeni en altta)
        visible_lines = self._lines[-max_visible:]

        clip = surface.get_clip()
        surface.set_clip(rect)

        y = rect.y + 24
        for line in visible_lines:
            color = _classify_color(line)
            # Uzun satırları kısalt
            if len(line) > 90:
                line = line[:87] + "..."
            rendered = self.font.render(line, True, color)
            surface.blit(rendered, (rect.x + 8, y))
            y += self.LINE_H

        surface.set_clip(clip)
