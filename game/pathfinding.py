"""
pathfinding.py — 20x20 / 30x30 Harita için Hafif A* (A-Star) Yol Bulma Sistemi
AI sadece hedef seçer, en kısa ve geçilebilir yolu bu modül hesaplar.
"""
from __future__ import annotations
import heapq
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game.map import GameMap, Tile


def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Manhattan mesafesi sezgiseli."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(
    game_map: "GameMap",
    start: tuple[int, int],
    goal: tuple[int, int],
    allow_water: bool = False,
    allow_mountain: bool = False,
) -> list[tuple[int, int]]:
    """
    A* algoritması ile start noktasından goal noktasına en kısa yolu bulur.
    Dönüş: [(x1, y1), (x2, y2), ...] şeklinde koordinat listesi (start hariç, goal dahil).
    Yol bulunamazsa boş liste [] döner.
    """
    if start == goal:
        return []

    from game.map import TileType

    # Öncelik kuyruğu: (f_score, counter, current_node)
    counter = 0
    open_set = []
    heapq.heappush(open_set, (0.0, counter, start))

    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}
    f_score: dict[tuple[int, int], float] = {start: heuristic(start, goal)}

    visited = set()

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current == goal:
            # Yolu geriye doğru inşa et
            path = []
            curr = goal
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.reverse()
            return path

        visited.add(current)
        cx, cy = current

        # 4 yönlü komşular (Yukarı, Aşağı, Sol, Sağ)
        neighbors = [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]

        for nx, ny in neighbors:
            if not (0 <= nx < game_map.WIDTH and 0 <= ny < game_map.HEIGHT):
                continue

            tile = game_map.get_tile(nx, ny)
            if not tile:
                continue

            # Geçiş kontrolü (Hedef hariç engellere bakılır)
            is_goal = (nx, ny) == goal
            if not is_goal:
                if tile.tile_type == TileType.WATER and not allow_water:
                    continue
                if tile.tile_type == TileType.MOUNTAIN and not allow_mountain:
                    continue

            # Yol maliyeti: Yollardan geçmek daha hızlı ve ucuzdur
            step_cost = 0.5 if tile.has_road else 1.0
            tentative_g = g_score[current] + step_cost

            if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                came_from[(nx, ny)] = current
                g_score[(nx, ny)] = tentative_g
                f = tentative_g + heuristic((nx, ny), goal)
                f_score[(nx, ny)] = f
                counter += 1
                heapq.heappush(open_set, (f, counter, (nx, ny)))

    return []
