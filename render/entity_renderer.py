"""
entity_renderer.py — Battle for Wesnoth Yüksek Çözünürlüklü Varlık Renderer'ı

Wesnoth'un orijinal şövalye, okçu, atlı elçi, kılıç ustası ve büyücü sprite'larını çizer.
"""
from __future__ import annotations

import math
import time
import pygame
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass
from collections import defaultdict

from ui.map_view import MapView
from game.entities import ArmyStatus, EnvoyStatus, UnitClass
from render.wesnoth_atlas import WesnothAtlas

if TYPE_CHECKING:
    from game.entities import EntityManager, ArmyEntity, EnvoyEntity
    from game.country import Country
    from render.camera import Camera

STACK_OFFSETS = [
    (0, 0),
    (-8, -8),
    (8, 8),
    (8, -8),
    (-8, 8),
    (0, -10),
    (0, 10),
]


@dataclass
class VisualState:
    curr_x: float
    curr_y: float
    start_x: float
    start_y: float
    target_x: float
    target_y: float
    elapsed: float = 0.0
    duration: float = 0.40
    is_moving: bool = False
    dir_x: float = 0.0
    dir_y: float = 0.0


class EntityRenderer:
    MOVE_DURATION = 0.40

    def __init__(self):
        self._font = None
        self._font_small = None
        self._visual_states: dict[str, VisualState] = {}
        self.atlas = WesnothAtlas.get()

    def _get_font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 11, bold=True)
        return self._font

    def _get_font_small(self):
        if self._font_small is None:
            self._font_small = pygame.font.SysFont("consolas", 9, bold=True)
        return self._font_small

    def update(self, dt: float) -> None:
        for state in self._visual_states.values():
            if state.is_moving:
                state.elapsed += dt
                if state.elapsed >= state.duration:
                    state.curr_x = state.target_x
                    state.curr_y = state.target_y
                    state.is_moving = False
                else:
                    t = min(1.0, max(0.0, state.elapsed / state.duration))
                    s = t * t * (3.0 - 2.0 * t)
                    state.curr_x = state.start_x + (state.target_x - state.start_x) * s
                    state.curr_y = state.start_y + (state.target_y - state.start_y) * s

    def _sync_entity_target(self, entity_id: str, sim_x: int, sim_y: int) -> VisualState:
        target_wx = sim_x * MapView.TILE_SIZE + MapView.TILE_SIZE // 2
        target_wy = sim_y * MapView.TILE_SIZE + MapView.TILE_SIZE // 2

        if entity_id not in self._visual_states:
            state = VisualState(
                curr_x=target_wx,
                curr_y=target_wy,
                start_x=target_wx,
                start_y=target_wy,
                target_x=target_wx,
                target_y=target_wy,
                elapsed=0.0,
                duration=self.MOVE_DURATION,
                is_moving=False,
            )
            self._visual_states[entity_id] = state
            return state

        state = self._visual_states[entity_id]
        if abs(state.target_x - target_wx) > 0.1 or abs(state.target_y - target_wy) > 0.1:
            dx = target_wx - state.curr_x
            dy = target_wy - state.curr_y
            dist = math.hypot(dx, dy)
            dir_x = (dx / dist) if dist > 0 else 0.0
            dir_y = (dy / dist) if dist > 0 else 0.0

            state.start_x = state.curr_x
            state.start_y = state.curr_y
            state.target_x = target_wx
            state.target_y = target_wy
            state.elapsed = 0.0
            state.duration = self.MOVE_DURATION
            state.is_moving = True
            state.dir_x = dir_x
            state.dir_y = dir_y

        return state

    def draw(
        self,
        surface: pygame.Surface,
        entities: "EntityManager",
        countries: list["Country"],
        camera: "Camera",
        hovered_entity_id: Optional[str] = None,
    ) -> None:
        country_colors = {c.agent_id: c.color for c in countries}
        world_rect = pygame.Rect(0, 0, camera.world_px_w, camera.world_px_h)
        visible = camera.get_source_rect().clip(world_rect)

        active_ids = set()
        tile_army_counts = defaultdict(list)
        for army in entities.armies.values():
            if army.is_alive():
                tile_army_counts[(army.x, army.y)].append(army.id)

        render_queue = []

        # 1. Ordular
        for army in entities.armies.values():
            if not army.is_alive():
                continue
            active_ids.add(army.id)
            state = self._sync_entity_target(army.id, army.x, army.y)
            is_hovered = (army.id == hovered_entity_id)

            armies_on_tile = tile_army_counts[(army.x, army.y)]
            idx = armies_on_tile.index(army.id) if army.id in armies_on_tile else 0
            offset = STACK_OFFSETS[idx % len(STACK_OFFSETS)] if len(armies_on_tile) > 1 else (0, 0)
            render_queue.append(("army", army, state, is_hovered, offset, state.curr_y + offset[1]))

        # 2. Elçiler (Envoys)
        for envoy in entities.envoys.values():
            active_ids.add(envoy.id)
            state = self._sync_entity_target(envoy.id, envoy.x, envoy.y)
            is_hovered = (envoy.id == hovered_entity_id)
            render_queue.append(("envoy", envoy, state, is_hovered, (0, 0), state.curr_y))

        # Y-Sorting (Derinlik)
        render_queue.sort(key=lambda item: item[5])

        for item in render_queue:
            if item[0] == "army":
                self._draw_wesnoth_army(surface, item[1], item[2], country_colors, camera, visible, item[3], item[4])
            else:
                self._draw_wesnoth_envoy(surface, item[1], item[2], country_colors, camera, visible, item[3])

        stale = [k for k in self._visual_states if k not in active_ids]
        for k in stale:
            del self._visual_states[k]

    def _draw_wesnoth_army(
        self,
        surface: pygame.Surface,
        army: "ArmyEntity",
        state: VisualState,
        country_colors: dict,
        camera: "Camera",
        visible: pygame.Rect,
        is_hovered: bool,
        stack_offset: tuple[int, int] = (0, 0),
    ) -> None:
        wx = state.curr_x + stack_offset[0]
        wy = state.curr_y + stack_offset[1]

        if not visible.collidepoint(wx, wy):
            return

        sx, sy = camera.world_to_screen(wx, wy)
        zoom = camera.zoom

        # Wesnoth orijinal sprite'ını al
        raw_sprite = self.atlas.get_unit_sprite(army.owner, army.unit_class)
        sw = max(18, int(36 * zoom))
        sh = max(18, int(36 * zoom))
        scaled_sprite = pygame.transform.scale(raw_sprite, (sw, sh))

        # 1. Zemin Gölgesi
        shadow_surf = pygame.Surface((sw, sh // 3), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (15, 18, 25, 110), (0, 0, sw, sh // 3))
        surface.blit(shadow_surf, (int(sx - sw // 2), int(sy + sh // 3)))

        # 2. Hover Highlight
        if is_hovered:
            pygame.draw.circle(surface, (255, 230, 70), (int(sx), int(sy)), int(sw // 2 + 4), 2)

        # 3. Sprite'ı Çiz
        # Yürüyüş sekmesi
        bounce_y = int(math.sin(time.perf_counter() * 12) * 2) if state.is_moving else 0
        surface.blit(scaled_sprite, (int(sx - sw // 2), int(sy - sh // 2 + bounce_y)))

        # 4. Can Barı (HP Bar)
        if zoom >= 0.65:
            bar_w = max(22, int(26 * zoom))
            bar_h = max(3, int(4 * zoom))
            bar_x = int(sx - bar_w // 2)
            bar_y = int(sy - sh // 2 - bar_h - 4)

            hp_ratio = max(0.0, min(1.0, army.hp / max(1.0, army.max_hp)))
            hp_color = (60, 230, 80) if hp_ratio > 0.5 else ((245, 190, 45) if hp_ratio > 0.25 else (235, 55, 55))

            pygame.draw.rect(surface, (10, 12, 18), (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2), border_radius=2)
            fill_w = int(bar_w * hp_ratio)
            if fill_w > 0:
                pygame.draw.rect(surface, hp_color, (bar_x, bar_y, fill_w, bar_h), border_radius=1)

        # 5. Birlik Güç Rozeti [ 🛡️ 40 ]
        if zoom >= 0.85:
            icon_p = {
                UnitClass.INFANTRY: "🛡️",
                UnitClass.ARCHER: "🏹",
                UnitClass.CAVALRY: "🐎",
                UnitClass.CATAPULT: "🧙",
            }.get(army.unit_class, "⚔️")
            text = f"{icon_p}{army.size}"
            font = self._get_font() if zoom >= 1.0 else self._get_font_small()
            label = font.render(text, True, (255, 255, 255))
            bw = label.get_width() + 6
            bh = label.get_height() + 2
            bx = int(sx) - bw // 2
            by = int(sy) + sh // 2 + 1

            pygame.draw.rect(surface, (14, 17, 24), (bx, by, bw, bh), border_radius=3)
            pygame.draw.rect(surface, (180, 190, 210), (bx, by, bw, bh), 1, border_radius=3)
            surface.blit(label, (bx + 3, by + 1))

    def _draw_wesnoth_envoy(
        self,
        surface: pygame.Surface,
        envoy: "EnvoyEntity",
        state: VisualState,
        country_colors: dict,
        camera: "Camera",
        visible: pygame.Rect,
        is_hovered: bool,
    ) -> None:
        wx = state.curr_x
        wy = state.curr_y

        if not visible.collidepoint(wx, wy):
            return

        sx, sy = camera.world_to_screen(wx, wy)
        zoom = camera.zoom

        raw_sprite = self.atlas.get_envoy_sprite(envoy.owner)
        sw = max(18, int(34 * zoom))
        sh = max(18, int(34 * zoom))
        scaled_sprite = pygame.transform.scale(raw_sprite, (sw, sh))

        # Atlı Elçi Gölgesi
        shadow_surf = pygame.Surface((sw, sh // 3), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (15, 18, 25, 110), (0, 0, sw, sh // 3))
        surface.blit(shadow_surf, (int(sx - sw // 2), int(sy + sh // 3)))

        if is_hovered:
            pygame.draw.circle(surface, (120, 230, 255), (int(sx), int(sy)), int(sw // 2 + 5), 2)

        bounce_y = int(math.sin(time.perf_counter() * 14) * 3) if state.is_moving else 0
        surface.blit(scaled_sprite, (int(sx - sw // 2), int(sy - sh // 2 + bounce_y)))

        # Elçi Mektup Rozeti [ 📜 ELÇİ ]
        if zoom >= 0.85:
            font = self._get_font_small()
            label = font.render("📜ELÇİ", True, (130, 230, 255))
            bw = label.get_width() + 6
            bh = label.get_height() + 2
            bx = int(sx) - bw // 2
            by = int(sy) + sh // 2 + 1

            pygame.draw.rect(surface, (14, 20, 32), (bx, by, bw, bh), border_radius=3)
            pygame.draw.rect(surface, (100, 200, 255), (bx, by, bw, bh), 1, border_radius=3)
            surface.blit(label, (bx + 3, by + 1))

    def get_hovered_entity(
        self,
        mouse_screen_pos: tuple[int, int],
        camera: "Camera",
        entities: "EntityManager",
        countries: list["Country"],
        map_offset: tuple[int, int] = (0, 0),
    ) -> Optional[dict]:
        mx = mouse_screen_pos[0] - map_offset[0]
        my = mouse_screen_pos[1] - map_offset[1]

        for army in entities.armies.values():
            if not army.is_alive() or army.id not in self._visual_states:
                continue
            st = self._visual_states[army.id]
            sx, sy = camera.world_to_screen(st.curr_x, st.curr_y)
            hit_r = max(16, int(16 * camera.zoom) + 4)
            if math.hypot(mx - sx, my - sy) <= hit_r:
                return {
                    "type": "army",
                    "id": army.id,
                    "owner": army.owner,
                    "class": army.unit_class.value.upper(),
                    "hp": f"{army.hp:.0f}/{army.max_hp:.0f}",
                    "atk": army.attack_power,
                    "def": army.defense_power,
                    "range": army.attack_range,
                    "size": army.size,
                    "status": army.status.value,
                    "skills": ", ".join(army.skills) if army.skills else "None",
                    "screen_x": mouse_screen_pos[0],
                    "screen_y": mouse_screen_pos[1],
                }

        for envoy in entities.envoys.values():
            if envoy.id not in self._visual_states:
                continue
            st = self._visual_states[envoy.id]
            sx, sy = camera.world_to_screen(st.curr_x, st.curr_y)
            hit_r = max(14, int(14 * camera.zoom) + 4)
            if math.hypot(mx - sx, my - sy) <= hit_r:
                return {
                    "type": "envoy",
                    "id": envoy.id,
                    "owner": envoy.owner,
                    "target": envoy.target_agent_id,
                    "screen_x": mouse_screen_pos[0],
                    "screen_y": mouse_screen_pos[1],
                }

        return None