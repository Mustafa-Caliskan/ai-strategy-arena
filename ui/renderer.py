"""
renderer.py — Ana Pygame render döngüsü

Phase 1: Kamera + önbelleğe alınmış terrain + viewport culling.

Render akışı:
  camera -> görünür world/source Rect -> cached terrain Surface
  -> görünür bölge -> scale/blit -> dinamik overlay'ler -> screen-space UI

Renderer, simülasyon state'ini asla mutate etmez; yalnızca ViewModel
üzerinden okur. Kontrol (pause/speed) TurnManager üzerinden yapılır.
"""
from __future__ import annotations
import asyncio
import pygame
import sys
from typing import Optional, TYPE_CHECKING

from ui.map_view   import MapView
from ui.scoreboard import Scoreboard
from ui.event_log  import EventLog
from ui.controls   import ControlPanel
from ui.dialog_overlay import DialogOverlay
from render.camera import Camera
from render.terrain_renderer import TerrainRenderer
from render.view_model import ViewModel
from render.entity_renderer import EntityRenderer

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

COLOR_BG   = (16,  18,  26)
COLOR_TITLE= (70,  80, 110)

# Kamera zoom adımı (mouse wheel başına)
ZOOM_STEP  = 1.1


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
        self.font_s  = pygame.font.SysFont("consolas", 12)
        self.font_m  = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_l  = pygame.font.SysFont("consolas", 16, bold=True)
        self.font_xl = pygame.font.SysFont("consolas", 20, bold=True)

        # Layout hesapla
        map_area_w = WIN_W - SIDEBAR_W
        map_area_h = WIN_H - EVENTLOG_H - CONTROLS_H

        self.map_rect      = pygame.Rect(0,          0,          map_area_w, map_area_h)
        self.sidebar_rect  = pygame.Rect(map_area_w, 0,          SIDEBAR_W,  WIN_H)
        self.eventlog_rect = pygame.Rect(0,          map_area_h, map_area_w, EVENTLOG_H)
        self.controls_rect = pygame.Rect(0,          map_area_h + EVENTLOG_H, map_area_w, CONTROLS_H)

        # Harita yüzeyi (her frame yeniden oluşturma — bir kez tahsis et)
        self.map_surf = pygame.Surface((map_area_w, map_area_h))

        # UI bileşenleri
        self.map_view    = MapView()
        self.entity_renderer = EntityRenderer()
        self.dialog_overlay  = DialogOverlay()
        self.scoreboard  = Scoreboard(self.font_s, self.font_m, self.font_l)
        self.event_log   = EventLog(self.font_s)
        self.controls    = ControlPanel(self.font_m)
        self.controls.build(
            self.controls_rect.x + 16,
            self.controls_rect.y + (CONTROLS_H - 32) // 2
        )

        # Kamera (dünya piksel boyutları GameMap sabitlerinden)
        from game.map import GameMap
        world_px_w = GameMap.WIDTH  * MapView.TILE_SIZE
        world_px_h = GameMap.HEIGHT * MapView.TILE_SIZE
        self.camera = Camera(world_px_w, world_px_h, map_area_w, map_area_h)

        # Renderer durumu
        self._running = True
        self._manager: Optional["TurnManager"] = None
        self._view: Optional[ViewModel] = None
        self._terrain: Optional[TerrainRenderer] = None
        self._last_turn = -1
        self._dragging = False
        self._drag_button = 0
        self._last_mouse = (0, 0)

    def set_manager(self, manager: "TurnManager") -> None:
        self._manager = manager
        self._view = ViewModel(manager)
        self._terrain = TerrainRenderer(manager.game_map, manager.countries)
        self._last_turn = manager.current_turn

    async def run_async(self, manager: "TurnManager") -> None:
        """Pygame döngüsünü async olarak çalıştır."""
        import time
        self.set_manager(manager)
        manager.speed_multiplier = self.controls.get_speed()

        last_time = time.perf_counter()
        while self._running:
            now = time.perf_counter()
            dt = max(0.001, min(0.1, now - last_time))
            last_time = now

            self._handle_events()
            self.entity_renderer.update(dt)
            self._render()
            self.clock.tick(FPS)
            # Pygame'in event loop'u bloklamasına izin verme
            await asyncio.sleep(1 / FPS)

    # ── Input ──────────────────────────────────────────────────────

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
                elif event.key == pygame.K_LEFT:
                    self.camera.pan(-20, 0)
                elif event.key == pygame.K_RIGHT:
                    self.camera.pan(20, 0)
                elif event.key == pygame.K_UP:
                    self.camera.pan(0, -20)
                elif event.key == pygame.K_DOWN:
                    self.camera.pan(0, 20)

            elif event.type == pygame.MOUSEWHEEL:
                # Yalnızca imleç harita alanı üzerindeyken zoom yap
                if self.map_rect.collidepoint(mouse_pos):
                    local = (mouse_pos[0] - self.map_rect.x,
                             mouse_pos[1] - self.map_rect.y)
                    factor = ZOOM_STEP if event.y > 0 else 1.0 / ZOOM_STEP
                    self.camera.zoom_at(factor, local[0], local[1])

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
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
                        if self._manager:
                            self._manager.is_running = False
                elif event.button in (2, 3):
                    # Orta/sağ tık: harita alanında pan başlat
                    if self.map_rect.collidepoint(mouse_pos):
                        self._dragging = True
                        self._drag_button = event.button
                        self._last_mouse = mouse_pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    self._dragging = False
                    self._drag_button = 0

            elif event.type == pygame.MOUSEMOTION:
                if self._dragging:
                    dx = mouse_pos[0] - self._last_mouse[0]
                    dy = mouse_pos[1] - self._last_mouse[1]
                    self.camera.pan(dx, dy)
                    self._last_mouse = mouse_pos

    def _toggle_pause(self) -> None:
        if self._manager:
            self._manager.is_paused = not self._manager.is_paused

    # ── Render ─────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self._manager or not self._view or not self._terrain:
            return

        # Terrain önbelleğini yalnızca tur değişince yeniden oluştur
        if self._view.current_turn != self._last_turn:
            self._terrain.mark_dirty()
            self._last_turn = self._view.current_turn

        self.screen.fill(COLOR_BG)

        # 1. Dünya (kamera + cached terrain + viewport culling)
        self._render_world()

        # Pause overlay
        if self._view.is_paused:
            overlay = pygame.Surface((self.map_rect.width, self.map_rect.height), pygame.SRCALPHA)
            overlay.fill((10, 12, 18, 140))
            self.screen.blit(overlay, self.map_rect.topleft)
            pt = self.font_xl.render("⏸ PAUSED — Press SPACE to resume", True, (255, 220, 60))
            px = self.map_rect.x + (self.map_rect.width - pt.get_width()) // 2
            py = self.map_rect.y + (self.map_rect.height - pt.get_height()) // 2
            self.screen.blit(pt, (px, py))

        # Winner overlay
        if self._view.winner:
            wt = self.font_xl.render(
                f"🏆 GAME OVER — {self._view.winner} WINS ({self._view.win_reason})",
                True, (255, 215, 0)
            )
            wx = self.map_rect.x + (self.map_rect.width - wt.get_width()) // 2
            wy = self.map_rect.y + 20
            pygame.draw.rect(self.screen, (20, 24, 36),
                             (wx - 12, wy - 8, wt.get_width() + 24, wt.get_height() + 16),
                             border_radius=8)
            pygame.draw.rect(self.screen, (255, 215, 0),
                             (wx - 12, wy - 8, wt.get_width() + 24, wt.get_height() + 16),
                             1, border_radius=8)
            self.screen.blit(wt, (wx, wy))

        # 2. Scoreboard (sağ panel)
        self.scoreboard.draw(
            self.screen,
            self._view.countries,
            self._view.diplomacy,
            self._view.current_turn,
            self._view.max_turns,
            self._view.winner,
            self.sidebar_rect,
        )

        # 3. Event Log (alt panel)
        self.event_log.update(self._view.events.get_recent_display(40))
        self.event_log.draw(self.screen, self.eventlog_rect)

        # 4. Kontroller
        pygame.draw.rect(self.screen, (24, 27, 38), self.controls_rect)
        pygame.draw.rect(self.screen, (48, 54, 76), self.controls_rect, 1)
        self.controls.draw(self.screen, pygame.mouse.get_pos(), self._view.is_paused)

        # Tur hızı göstergesi
        spd = self.font_s.render(
            f"Speed: x{self._view.speed_multiplier:.0f}  |  "
            f"SPACE=Pause  ESC=Quit  Wheel=Zoom  Drag=Pan",
            True, (140, 150, 175)
        )
        self.screen.blit(spd, (self.controls_rect.x + 470, self.controls_rect.y + 22))

        # 5. Kraliyet Diyalog ve Strateji Kartı (Overlay)
        dec = self._view.latest_decision
        if dec:
            speaker = "OpenAI (GPT-4o)" if dec.get("agent_id") == "AI_A" else "DeepSeek"
            orders = f"{dec.get('action', '')} {dec.get('sub_action') or ''} {dec.get('target') or ''}".strip()
            self.dialog_overlay.show_turn_decision(
                speaker=speaker,
                thought=dec.get("thought", ""),
                orders=orders,
                letter=dec.get("diplomatic_message"),
                turn=dec.get("turn", self._view.current_turn),
            )
        self.dialog_overlay.draw(self.screen, WIN_W, WIN_H)

        # 6. Screen-Space Entity Hover Tooltip
        self._render_tooltip()

        pygame.display.flip()

    def _render_world(self) -> None:
        """Kamera + cached terrain + viewport culling ile dünyayı çizer."""
        self.map_surf.fill((16, 18, 26))

        terrain = self._terrain.surface
        world_rect = pygame.Rect(0, 0, self._terrain.world_px_w, self._terrain.world_px_h)

        # Görünür world bölgesi (viewport culling)
        src_rect = self.camera.get_source_rect()
        clamped = src_rect.clip(world_rect)

        if clamped.width > 0 and clamped.height > 0:
            sub = terrain.subsurface(clamped)

            dest_w = clamped.width * self.camera.zoom
            dest_h = clamped.height * self.camera.zoom
            dest_x = (clamped.x - src_rect.x) * self.camera.zoom
            dest_y = (clamped.y - src_rect.y) * self.camera.zoom

            if self.camera.zoom < 1.0:
                scaled = pygame.transform.smoothscale(
                    sub, (max(1, int(dest_w)), max(1, int(dest_h)))
                )
            else:
                scaled = pygame.transform.scale(
                    sub, (max(1, int(dest_w)), max(1, int(dest_h)))
                )

            self.map_surf.blit(scaled, (int(dest_x), int(dest_y)))

        # Dinamik overlay'ler (sınırlar + başkentler) — her frame
        self.map_view.draw_dynamic(
            self.map_surf, self._view.game_map, self._view.countries, self.camera
        )

        # Hover tespiti
        mouse_pos = pygame.mouse.get_pos()
        self._hovered_info = None
        if self.map_rect.collidepoint(mouse_pos):
            self._hovered_info = self.entity_renderer.get_hovered_entity(
                mouse_pos, self.camera, self._view.entities, self._view.countries, (self.map_rect.x, self.map_rect.y)
            )

        hovered_id = self._hovered_info["id"] if self._hovered_info else None

        # Dinamik entity'ler (ordular + elçiler) — her frame
        self.entity_renderer.draw(
            self.map_surf, self._view.entities, self._view.countries, self.camera, hovered_entity_id=hovered_id
        )

        # Harita alanına blit
        self.screen.blit(self.map_surf, self.map_rect.topleft)
        pygame.draw.rect(self.screen, (48, 54, 76), self.map_rect, 1)

    def _render_tooltip(self) -> None:
        """Screen-space modern kart tooltip çizer."""
        if not getattr(self, "_hovered_info", None):
            return

        info = self._hovered_info
        mx, my = info["screen_x"], info["screen_y"]

        if info["type"] == "army":
            lines = [
                f"⚔️ {info['id']} ({info.get('class', 'INFANTRY')})",
                f"Owner: {info['owner']}  |  HP: {info.get('hp', '100/100')}",
                f"Combat: ATK {info.get('atk', 20)} | DEF {info.get('def', 10)} | RNG {info.get('range', 1)}",
                f"Skills: {info.get('skills', 'None')}",
                f"Status: {info['status'].upper()} ({info['size']} soldiers)",
            ]
            border_col = (255, 215, 60)
        else:
            lines = [
                f"📜 DIPLOMATIC ENVOY: {info['id']}",
                f"From: {info['owner']} ➔ {info['target']}",
                "Payload: Peace Proposal",
                "Status: EN ROUTE",
            ]
            border_col = (110, 210, 255)

        rendered_lines = [self.font_s.render(l, True, (240, 245, 255)) for l in lines]
        tw = max(r.get_width() for r in rendered_lines) + 20
        th = sum(r.get_height() for r in rendered_lines) + 16

        # Tooltip konumunu ekran sınırlarına göre ayarla
        tx = mx + 16
        ty = my + 16
        if tx + tw > WIN_W - SIDEBAR_W:
            tx = mx - tw - 12
        if ty + th > WIN_H - CONTROLS_H:
            ty = my - th - 12

        # Drop shadow
        pygame.draw.rect(self.screen, (10, 12, 18), (tx + 3, ty + 3, tw, th), border_radius=6)
        # Main card
        tip_rect = pygame.Rect(tx, ty, tw, th)
        pygame.draw.rect(self.screen, (24, 27, 38), tip_rect, border_radius=6)
        pygame.draw.rect(self.screen, border_col, tip_rect, 1, border_radius=6)

        curr_y = ty + 8
        for r in rendered_lines:
            self.screen.blit(r, (tx + 10, curr_y))
            curr_y += r.get_height()
