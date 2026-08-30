"""
controls.py — Modern Strateji Oyunu Alt Kontrol Çubuğu (Grand Strategy Bar)
"""
from __future__ import annotations
import pygame

COLOR_BAR_BG    = (24,  27,  38)
COLOR_BORDER    = (48,  54,  76)
COLOR_BTN       = (36,  42,  60)
COLOR_BTN_HOVER = (52,  60,  85)
COLOR_BTN_ACT   = (80,  65, 120)
COLOR_BTN_BORDER= (65,  75, 105)
COLOR_TEXT      = (230, 235, 245)
COLOR_PAUSE     = (255, 190,  60)
COLOR_RUN       = (90,  215,  90)


class Button:
    def __init__(self, rect: pygame.Rect, label: str, action: str):
        self.rect   = rect
        self.label  = label
        self.action = action
        self.active = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, hovered: bool = False) -> None:
        col = COLOR_BTN_ACT if self.active else (COLOR_BTN_HOVER if hovered else COLOR_BTN)
        border_col = (255, 215, 100) if self.active else ((120, 140, 180) if hovered else COLOR_BTN_BORDER)

        pygame.draw.rect(surface, col, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_col, self.rect, 1, border_radius=6)

        text = font.render(self.label, True, COLOR_TEXT)
        tx = self.rect.x + (self.rect.width  - text.get_width())  // 2
        ty = self.rect.y + (self.rect.height - text.get_height()) // 2
        surface.blit(text, (tx, ty))

    def is_clicked(self, pos: tuple) -> bool:
        return self.rect.collidepoint(pos)


class ControlPanel:
    """Modern grand strategy kontrol paneli."""

    BTN_W   = 100
    BTN_H   = 32
    BTN_GAP = 10

    def __init__(self, font):
        self.font = font
        self.buttons: list[Button] = []
        self._speed_index = 0
        self._speeds = [1.0, 2.0, 4.0, 8.0]
        self._speed_labels = ["Speed x1", "Speed x2", "Speed x4", "Speed x8"]

    def build(self, x: int, y: int) -> None:
        """Butonları verilen konumda oluştur."""
        self.buttons = []
        bw, bh, gap = self.BTN_W, self.BTN_H, self.BTN_GAP

        defs = [
            ("⏸ Pause",    "pause"),
            ("▶ Resume",   "resume"),
            (f"⚡ {self._speed_labels[self._speed_index]}", "speed"),
            ("🔄 Restart",  "restart"),
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
        for btn in self.buttons:
            if btn.is_clicked(pos):
                if btn.action == "speed":
                    self._speed_index = (self._speed_index + 1) % len(self._speeds)
                    btn.label = f"⚡ {self._speed_labels[self._speed_index]}"
                return btn.action
        return None

    def get_speed(self) -> float:
        return self._speeds[self._speed_index]