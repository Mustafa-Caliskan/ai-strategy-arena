"""
renderer.py — Ana Pygame render döngüsü
Async-safe: asyncio event loop ile Pygame birlikte çalışır.
"""
from __future__ import annotations
import asyncio
import pygame
import sys
import os
from typing import Optional, TYPE_CHECKING

from ui.map_view   import MapView
from ui.scoreboard import Scoreboard
from ui.event_log  import EventLog
from ui.controls   import ControlPanel

if TYPE_CHECKING:
    from simulation.turn_manager import TurnManager

# ── Pencere boyutları ─────────────────────────────────────────────
WIN_W      = 1280
WIN_H      = 820
FPS        = 30

# Layout bölgeleri
SIDEBAR_W  = 300
EVENTLOG_H = 180
CONTROLS_H = 60

COLOR_BG   = (12,  12,  22)
COLOR_TITLE= (80, 80, 120)


class GameRenderer:
    """
    Pygame penceresini yönetir.
    TurnManager async döngüsüyle paralel çalışır.
    """

    def __init__(self, title: str = "AI Strategy Arena"):
        pygame.init()
        pygame.display.set_caption(title)
        self.screen  = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock   = pygame.time.Clock()

        # Font yükleme
        font_path = None  # sistem fontu kullan
        self.font_s  = pygame.font.SysFont("consolas", 13)
        self.font_m  = pygame.font.SysFont("consolas", 15, bold=True)
        self.font_l  = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_xl = pygame.font.SysFont("consolas", 22, bold=True)

        # Layout hesapla
        map_area_w = WIN_W - SIDEBAR_W
        map_area_h = WIN_H - EVENTLOG_H - CONTROLS_H

        self.map_rect      = pygame.Rect(0,          0,          map_area_w, map_area_h)
        self.sidebar_rect  = pygame.Rect(map_area_w, 0,          SIDEBAR_W,  WIN_H)
        self.eventlog_rect = pygame.Rect(0,          map_area_h, map_area_w, EVENTLOG_H)
        self.controls_rect = pygame.Rect(0,          map_area_h + EVENTLOG_H, map_area_w, CONTROLS_H)

        # Harita offset (ortalama)
        from game.map import GameMap
        map_px_w = GameMap.WIDTH  * 36
        map_px_h = GameMap.HEIGHT * 36
        self.map_offset_x = max(0, (map_area_w - map_px_w) // 2)
        self.map_offset_y = max(0, (map_area_h - map_px_h) // 2)

        # UI bileşenleri
        self.map_view    = MapView()
        self.scoreboard  = Scoreboard(self.font_s, self.font_m, self.font_l)
        self.event_log   = EventLog(self.font_s)
        self.controls    = ControlPanel(self.font_m)
        self.controls.build(
            self.controls_rect.x + 16,
            self.controls_rect.y + (CONTROLS_H - 34) // 2
        )

        self._running = True
        self._manager: Optional["TurnManager"] = None

    def set_manager(self, manager: "TurnManager") -> None:
        self._manager = manager

    async def run_async(self, manager: "TurnManager") -> None:
        """Pygame döngüsünü async olarak çalıştır."""
        self._manager = manager
        manager.speed_multiplier = self.controls.get_speed()

        while self._running:
            self._handle_events()
            self._render()
            self.clock.tick(FPS)
            # Pygame'in event loop'u bloklamasına izin verme
            await asyncio.sleep(1 / FPS)

    def _handle_events(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                if self._manager:
                    self._manager.is_running = False
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self._toggle_pause()
                elif event.key == pygame.K_ESCAPE:
                    self._running = False
                    if self._manager:
                        self._manager.is_running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.controls.handle_click(mouse_pos)
                if action == "pause":
                    if self._manager:
                        self._manager.is_paused = True
                elif action == "resume":
                    if self._manager:
                        self._manager.is_paused = False
                elif action == "speed":
                    if self._manager:
                        self._manager.speed_multiplier = self.controls.get_speed()
                elif action == "restart":
                    # Restart: dışarıdan handle edilir
                    if self._manager:
                        self._manager.is_running = False

    def _toggle_pause(self) -> None:
        if self._manager:
            self._manager.is_paused = not self._manager.is_paused

    def _render(self) -> None:
        if not self._manager:
            return

        m = self._manager
        self.screen.fill(COLOR_BG)

        # 1. Harita
        map_surf = pygame.Surface((self.map_rect.width, self.map_rect.height))
        map_surf.fill((18, 18, 30))
        self.map_view.draw(
            map_surf,
            m.game_map,
            m.countries,
            offset_x=self.map_offset_x,
            offset_y=self.map_offset_y,
        )
        self.screen.blit(map_surf, self.map_rect.topleft)
        pygame.draw.rect(self.screen, (50, 50, 80), self.map_rect, 1)

        # Pause overlay
        if m.is_paused:
            overlay = pygame.Surface((self.map_rect.width, self.map_rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, self.map_rect.topleft)
            pt = self.font_xl.render("⏸ PAUSED — Press SPACE to resume", True, (255, 220, 50))
            px = self.map_rect.x + (self.map_rect.width - pt.get_width()) // 2
            py = self.map_rect.y + (self.map_rect.height - pt.get_height()) // 2
            self.screen.blit(pt, (px, py))

        # Winner overlay
        if m.winner:
            wt = self.font_xl.render(
                f"🏆 GAME OVER — {m.winner} WINS ({m.win_reason})",
                True, (255, 215, 0)
            )
            wx = self.map_rect.x + (self.map_rect.width - wt.get_width()) // 2
            wy = self.map_rect.y + 20
            pygame.draw.rect(self.screen, (20, 20, 40),
                             (wx - 10, wy - 8, wt.get_width() + 20, wt.get_height() + 16),
                             border_radius=8)
            self.screen.blit(wt, (wx, wy))

        # 2. Scoreboard (sağ panel)
        self.scoreboard.draw(
            self.screen,
            m.countries,
            m.diplomacy,
            m.current_turn,
            m.max_turns,
            m.winner,
            self.sidebar_rect,
        )

        # 3. Event Log (alt panel)
        self.event_log.update(m.events.get_recent_display(40))
        self.event_log.draw(self.screen, self.eventlog_rect)

        # 4. Kontroller
        pygame.draw.rect(self.screen, (20, 20, 35), self.controls_rect)
        pygame.draw.rect(self.screen, (50, 50, 80), self.controls_rect, 1)
        self.controls.draw(self.screen, pygame.mouse.get_pos(), m.is_paused)

        # Tur hızı göstergesi
        spd = self.font_s.render(
            f"Speed: x{self._manager.speed_multiplier:.0f}  |  "
            f"SPACE=Pause  ESC=Quit",
            True, (120, 120, 150)
        )
        self.screen.blit(spd, (self.controls_rect.x + 430, self.controls_rect.y + 22))

        pygame.display.flip()
