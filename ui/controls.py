"""
controls.py — Pause / Resume / Speed / Restart kontrolleri
"""
from __future__ import annotations
import pygame

COLOR_BTN       = (50,  50,  80)
COLOR_BTN_HOVER = (70,  70, 110)
COLOR_BTN_ACT   = (90,  60, 140)
COLOR_TEXT      = (220, 220, 230)
COLOR_BORDER    = (100, 100, 150)
COLOR_PAUSE     = (255, 180,  50)
COLOR_RUN       = (80,  200,  80)


class Button:
    def __init__(self, rect: pygame.Rect, label: str, action: str):
        self.rect   = rect
        self.label  = label
        self.action = action
        self.active = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, hovered: bool = False) -> None:
        col = COLOR_BTN_ACT if self.active else (COLOR_BTN_HOVER if hovered else COLOR_BTN)
        pygame.draw.rect(surface, col, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, self.rect, 1, border_radius=6)
        text = font.render(self.label, True, COLOR_TEXT)
        tx = self.rect.x + (self.rect.width  - text.get_width())  // 2
        ty = self.rect.y + (self.rect.height - text.get_height()) // 2
        surface.blit(text, (tx, ty))

    def is_clicked(self, pos: tuple) -> bool:
        return self.rect.collidepoint(pos)


class ControlPanel:
    """Pause/Resume/Speed/Restart buton grubu."""

    BTN_W  = 90
    BTN_H  = 34
    BTN_GAP = 8

    def __init__(self, font):
        self.font = font
        self.buttons: list[Button] = []
        self._speed_index = 0
        self._speeds = [1.0, 2.0, 4.0]
        self._speed_labels = ["Speed x1", "Speed x2", "Speed x4"]

    def build(self, x: int, y: int) -> None:
        """Butonları verilen konumda oluştur."""
        self.buttons = []
        bw, bh, gap = self.BTN_W, self.BTN_H, self.BTN_GAP

        defs = [
            ("Pause",    "pause"),
            ("Resume",   "resume"),
            (self._speed_labels[self._speed_index], "speed"),
            ("Restart",  "restart"),
        ]
        for i, (label, action) in enumerate(defs):
            rect = pygame.Rect(x + i * (bw + gap), y, bw, bh)
            self.buttons.append(Button(rect, label, action))

    def draw(self, surface: pygame.Surface, mouse_pos: tuple, is_paused: bool) -> None:
        for btn in self.buttons:
            hovered = btn.rect.collidepoint(mouse_pos)
            if btn.action == "pause":
                btn.active = is_paused
            elif btn.action == "resume":
                btn.active = not is_paused
            btn.draw(surface, self.font, hovered)

    def handle_click(self, pos: tuple) -> str | None:
        """Tıklanan butonun action'ını döndür."""
        for btn in self.buttons:
            if btn.is_clicked(pos):
                if btn.action == "speed":
                    self._speed_index = (self._speed_index + 1) % len(self._speeds)
                    btn.label = self._speed_labels[self._speed_index]
                return btn.action
        return None

    def get_speed(self) -> float:
        return self._speeds[self._speed_index]
