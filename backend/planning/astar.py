"""
Path planning (spec §12). A* over the occupancy grid — grid cells marked
FREE or UNKNOWN are traversable (UNKNOWN is treated as passable-but-risky
via a cost penalty rather than a hard block, so the UGV isn't stuck the
moment it hasn't seen a patch of ground yet); OCC_OBSTACLE (after
inflation) is not.

Planner is an interface so Dijkstra / RRT / RRT* / D* Lite can be added
later (spec's stated future-algorithm list) without touching
communication/state_manager.py, which only calls Planner.plan(...).
"""
from __future__ import annotations

import abc
import heapq
from dataclasses import dataclass

import numpy as np

from config.status_labels import ModuleStatus
from mapping.occupancy_grid import OccupancyGrid, FREE, OCC_OBSTACLE, OCC_UNKNOWN


@dataclass
class PlanResult:
    waypoints_world: list[tuple[float, float]]  # [(x, y), ...] in meters, world frame
    found: bool
    status: ModuleStatus


class Planner(abc.ABC):
    status: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED

    @abc.abstractmethod
    def plan(self, grid: OccupancyGrid, start_world: tuple[float, float],
             goal_world: tuple[float, float]) -> PlanResult:
        ...


_UNKNOWN_COST_PENALTY = 3.0  # multiplier on step cost when crossing UNKNOWN cells

_NEIGHBORS_8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


class AStarPlanner(Planner):
    status = ModuleStatus.ACTIVE

    def __init__(self, obstacle_inflation_cells: int = 1) -> None:
        self._inflation = obstacle_inflation_cells

    def plan(self, grid: OccupancyGrid, start_world: tuple[float, float],
             goal_world: tuple[float, float]) -> PlanResult:
        cost_grid = grid.inflate_obstacles(self._inflation)

        start = grid.world_to_cell(*start_world)
        goal = grid.world_to_cell(*goal_world)

        if not grid.in_bounds(*start) or not grid.in_bounds(*goal):
            return PlanResult(waypoints_world=[], found=False, status=ModuleStatus.ACTIVE)
        if cost_grid[goal[1], goal[0]] == OCC_OBSTACLE:
            return PlanResult(waypoints_world=[], found=False, status=ModuleStatus.ACTIVE)

        path_cells = self._search(cost_grid, start, goal)
        if path_cells is None:
            return PlanResult(waypoints_world=[], found=False, status=ModuleStatus.ACTIVE)

        waypoints = [grid.cell_to_world(cx, cy) for cx, cy in self._simplify(path_cells)]
        return PlanResult(waypoints_world=waypoints, found=True, status=ModuleStatus.ACTIVE)

    def _search(self, cost_grid: np.ndarray, start: tuple[int, int],
                goal: tuple[int, int]) -> list[tuple[int, int]] | None:
        n = cost_grid.shape[0]

        def h(a: tuple[int, int], b: tuple[int, int]) -> float:
            return float(np.hypot(a[0] - b[0], a[1] - b[1]))

        open_set: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0.0}
        visited: set[tuple[int, int]] = set()

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                return self._reconstruct(came_from, current)
            if current in visited:
                continue
            visited.add(current)

            cx, cy = current
            for dx, dy in _NEIGHBORS_8:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < n and 0 <= ny < n):
                    continue
                cell_val = cost_grid[ny, nx]
                if cell_val == OCC_OBSTACLE:
                    continue

                step_cost = np.hypot(dx, dy)
                if cell_val == OCC_UNKNOWN:
                    step_cost *= _UNKNOWN_COST_PENALTY

                tentative_g = g_score[current] + step_cost
                neighbor = (nx, ny)
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + h(neighbor, goal)
                    heapq.heappush(open_set, (f, neighbor))

        return None

    @staticmethod
    def _reconstruct(came_from: dict, current: tuple[int, int]) -> list[tuple[int, int]]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    @staticmethod
    def _simplify(path_cells: list[tuple[int, int]], every: int = 4) -> list[tuple[int, int]]:
        """Thin a dense cell-by-cell path down to a manageable waypoint list
        (every Nth cell, plus the final goal cell) — the controller
        interpolates between waypoints, it doesn't need every grid cell."""
        if len(path_cells) <= 2:
            return path_cells
        simplified = path_cells[::every]
        if simplified[-1] != path_cells[-1]:
            simplified.append(path_cells[-1])
        return simplified


def create_planner(algorithm: str = "astar") -> Planner:
    if algorithm == "astar":
        return AStarPlanner()
    raise ValueError(f"Unknown/unimplemented planning algorithm: {algorithm}")
