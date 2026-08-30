"""
terrain_renderer.py — Cached terrain surface builder.

Builds a single Pygame Surface representing the static terrain (tiles,
terrain details, roads and buildings) and reuses it across frames. The
surface is rebuilt only when terrain-related rendering data changes
(e.g. after a turn, when buildings/roads/territory may have changed).

This module never mutates simulation state; it only reads GameMap/Tile
data to produce a visual surface.
"""
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING

from ui.map_view import MapView

if TYPE_CHECKING:
    from game.map import GameMap
    from game.country import Country


class TerrainRenderer:
    """Caches the static terrain into a Pygame Surface."""

    def __init__(self, game_map: "GameMap", countries: list["Country"]):
        self.game_map = game_map
        self.countries = countries
        self.tile_size = MapView.TILE_SIZE
        self.world_px_w = game_map.WIDTH * self.tile_size
        self.world_px_h = game_map.HEIGHT * self.tile_size
        self._surface: pygame.Surface | None = None
        self._dirty = True

    @property
    def surface(self) -> pygame.Surface:
        """The cached terrain surface, rebuilt if dirty."""
        if self._surface is None or self._dirty:
            self._rebuild()
        return self._surface

    def mark_dirty(self) -> None:
        """Flag the cached surface for rebuild on next access."""
        self._dirty = True

    def _rebuild(self) -> None:
        """(Re)build the cached terrain surface from current GameMap data."""
        surf = pygame.Surface((self.world_px_w, self.world_px_h))
        surf.fill((18, 18, 30))

        # Reuse MapView's drawing primitives to preserve the existing look.
        view = MapView(self.game_map.WIDTH, self.game_map.HEIGHT)
        view.draw_terrain(surf, self.game_map, self.countries)

        self._surface = surf
        self._dirty = False
