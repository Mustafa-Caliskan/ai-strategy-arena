"""
camera.py — Viewport camera with pan, zoom and coordinate transforms.

The camera is the single source of truth for the view-space transform
applied to the world every frame. It operates in world-pixel coordinates
and never mutates simulation state.

Coordinate model:
  - World pixel space: the cached terrain surface is world_px_w x world_px_h.
  - Screen space: the map viewport area where the world is drawn.
  - (cam.x, cam.y) is the top-left of the visible viewport in world pixels.
  - zoom scales world pixels to screen pixels.
"""
from __future__ import annotations

import pygame


class Camera:
    """2-D pan/zoom camera that maps world pixels to screen pixels."""

    MIN_ZOOM = 0.5
    MAX_ZOOM = 3.0

    def __init__(
        self,
        world_px_w: int,
        world_px_h: int,
        view_w: int,
        view_h: int,
    ):
        self.world_px_w = world_px_w
        self.world_px_h = world_px_h
        self.view_w = view_w
        self.view_h = view_h
        self.zoom = 1.0
        # Center the world in the viewport initially.
        self.x = (world_px_w - view_w / self.zoom) / 2
        self.y = (world_px_h - view_h / self.zoom) / 2
        self.clamp()

    def set_view(self, view_w: int, view_h: int) -> None:
        """Update the viewport size (e.g. on window resize)."""
        self.view_w = view_w
        self.view_h = view_h
        self.clamp()

    def clamp(self) -> None:
        """Keep the camera inside the world bounds (or center it if the
        viewport is larger than the world)."""
        view_w_px = self.view_w / self.zoom
        view_h_px = self.view_h / self.zoom

        if view_w_px >= self.world_px_w:
            self.x = (self.world_px_w - view_w_px) / 2
        else:
            self.x = max(0.0, min(self.x, self.world_px_w - view_w_px))

        if view_h_px >= self.world_px_h:
            self.y = (self.world_px_h - view_h_px) / 2
        else:
            self.y = max(0.0, min(self.y, self.world_px_h - view_h_px))

    def pan(self, dx: float, dy: float) -> None:
        """Pan by screen-space pixel deltas (pre-zoom)."""
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom
        self.clamp()

    def zoom_at(self, factor: float, screen_x: float, screen_y: float) -> None:
        """Zoom towards a screen anchor so the world point under the cursor
        stays fixed. factor > 1 zooms in, factor < 1 zooms out."""
        world_before = self.screen_to_world(screen_x, screen_y)
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        world_after = self.screen_to_world(screen_x, screen_y)
        self.x += world_before[0] - world_after[0]
        self.y += world_before[1] - world_after[1]
        self.clamp()

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Map world-pixel coordinates to screen coordinates."""
        return ((wx - self.x) * self.zoom, (wy - self.y) * self.zoom)

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Map screen coordinates to world-pixel coordinates."""
        return (sx / self.zoom + self.x, sy / self.zoom + self.y)

    def get_source_rect(self) -> pygame.Rect:
        """World-pixel rect visible through the viewport (may extend past the
        world bounds; callers should clip it)."""
        w = self.view_w / self.zoom
        h = self.view_h / self.zoom
        return pygame.Rect(int(self.x), int(self.y), int(w), int(h))
