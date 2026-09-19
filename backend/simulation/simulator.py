"""
UGV simulator (spec §16). A lightweight differential-drive kinematic model
that the *real* planner and motion controller drive — this module does not
fake navigation results; it integrates whatever VelocityCommand the
controller actually sends, and reports a real collision if the simulated
UGV footprint overlaps an occupied grid cell.

Status: SIMULATED (that's its entire purpose — standing in for a physical
UGV chassis during development), but the kinematics/integration and
collision checks are real computation, not scripted/pre-baked motion.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from config.status_labels import ModuleStatus
from mapping.occupancy_grid import OccupancyGrid, OCC_OBSTACLE


@dataclass
class SimulatedUGVState:
    x: float = 0.0
    y: float = 0.0
    heading_deg: float = 0.0
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    distance_travelled_m: float = 0.0
    collided: bool = False
    trajectory: list[tuple[float, float]] = field(default_factory=list)


class UGVSimulator:
    status = ModuleStatus.SIMULATED

    # Rough footprint radius (meters) for collision checking — a small
    # rover-class UGV, not calibrated to any specific chassis yet.
    footprint_radius_m = 0.35

    def __init__(self) -> None:
        self.state = SimulatedUGVState()
        self._last_tick_time: float | None = None
        self.state.trajectory.append((0.0, 0.0))

    def reset(self, x: float = 0.0, y: float = 0.0, heading_deg: float = 0.0) -> None:
        self.state = SimulatedUGVState(x=x, y=y, heading_deg=heading_deg)
        self.state.trajectory.append((x, y))
        self._last_tick_time = None

    def apply_velocity(self, linear_velocity: float, angular_velocity: float) -> None:
        self.state.linear_velocity = linear_velocity
        self.state.angular_velocity = angular_velocity

    def tick(self, grid: OccupancyGrid | None = None) -> SimulatedUGVState:
        now = time.monotonic()
        dt = 0.0 if self._last_tick_time is None else min(0.5, now - self._last_tick_time)
        self._last_tick_time = now

        if dt > 0 and not self.state.collided:
            heading_rad = np.radians(self.state.heading_deg)
            dx = self.state.linear_velocity * np.cos(heading_rad) * dt
            dy = self.state.linear_velocity * np.sin(heading_rad) * dt

            self.state.x += dx
            self.state.y += dy
            self.state.heading_deg = (self.state.heading_deg + np.degrees(self.state.angular_velocity) * dt) % 360.0
            self.state.distance_travelled_m += float(np.hypot(dx, dy))
            self.state.trajectory.append((round(self.state.x, 3), round(self.state.y, 3)))
            if len(self.state.trajectory) > 500:
                self.state.trajectory.pop(0)

            if grid is not None:
                self.state.collided = self._check_collision(grid)

        return self.state

    def _check_collision(self, grid: OccupancyGrid) -> bool:
        cx, cy = grid.world_to_cell(self.state.x, self.state.y)
        radius_cells = max(1, int(round(self.footprint_radius_m / grid.cell_size_m)))
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                gx, gy = cx + dx, cy + dy
                if grid.in_bounds(gx, gy) and grid.grid[gy, gx] == OCC_OBSTACLE:
                    if np.hypot(dx, dy) * grid.cell_size_m <= self.footprint_radius_m:
                        return True
        return False

    def distance_to(self, x: float, y: float) -> float:
        return float(np.hypot(x - self.state.x, y - self.state.y))
