"""
Local map (spec §11): a 2D occupancy grid in the UGV's local coordinate
frame (meters, origin at the UGV's start position — no GPS). Continuously
updated from the traversability mask, projected into ground-plane
coordinates directly in front of the UGV using a flat-ground assumption.

Status: ACTIVE. The projection is intentionally simple (flat-ground,
fixed camera pitch) — accurate enough for a near-field planning horizon on
gentle outdoor terrain, not a substitute for real depth sensing on rough
terrain. That limitation is documented here rather than hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config.status_labels import ModuleStatus
from perception.traversability import TRAVERSABLE, OBSTACLE, UNKNOWN, TraversabilityResult

FREE = 0
OCC_OBSTACLE = 1
OCC_UNKNOWN = 2


@dataclass
class OccupancyGrid:
    size_m: float
    cell_size_m: float
    grid: np.ndarray = field(init=False)  # int8, values in {FREE, OCC_OBSTACLE, OCC_UNKNOWN}
    status: ModuleStatus = ModuleStatus.ACTIVE

    def __post_init__(self) -> None:
        n = int(self.size_m / self.cell_size_m)
        self.n_cells = n
        self.grid = np.full((n, n), OCC_UNKNOWN, dtype=np.int8)
        # Grid is centered on the origin: cell (n//2, n//2) == world (0, 0).
        self.origin_cell = n // 2

    def world_to_cell(self, x: float, y: float) -> tuple[int, int]:
        cx = self.origin_cell + int(round(x / self.cell_size_m))
        cy = self.origin_cell + int(round(y / self.cell_size_m))
        return cx, cy

    def cell_to_world(self, cx: int, cy: int) -> tuple[float, float]:
        x = (cx - self.origin_cell) * self.cell_size_m
        y = (cy - self.origin_cell) * self.cell_size_m
        return x, y

    def in_bounds(self, cx: int, cy: int) -> bool:
        return 0 <= cx < self.n_cells and 0 <= cy < self.n_cells

    def update_from_traversability(
        self,
        trav: TraversabilityResult,
        ugv_x: float,
        ugv_y: float,
        ugv_heading_deg: float,
        max_range_m: float = 8.0,
        fov_deg: float = 70.0,
    ) -> None:
        """Project the near-field rows of the traversability mask onto the
        ground plane in front of the UGV using a flat-ground, fixed-pitch
        assumption, and stamp the result into the grid.

        This deliberately only projects the bottom ~40% of the mask (the
        region closest to the camera, where the flat-ground assumption is
        least wrong) rather than the whole frame.
        """
        h, w = trav.mask.shape
        heading_rad = np.radians(ugv_heading_deg)
        half_fov_rad = np.radians(fov_deg / 2)

        near_rows = range(int(h * 0.6), h, 4)  # subsample rows for speed
        for row in near_rows:
            # Row closer to the bottom of the frame == closer to the UGV.
            depth_frac = (h - row) / (h * 0.4)  # 0 near bottom .. 1 at the 60% cutoff
            range_m = max(0.3, depth_frac * max_range_m)

            for col in range(0, w, 4):
                bearing_frac = (col / w) - 0.5  # -0.5 .. 0.5 across the frame
                bearing_rad = bearing_frac * 2 * half_fov_rad

                world_bearing = heading_rad + bearing_rad
                wx = ugv_x + range_m * np.cos(world_bearing)
                wy = ugv_y + range_m * np.sin(world_bearing)

                cx, cy = self.world_to_cell(wx, wy)
                if not self.in_bounds(cx, cy):
                    continue

                val = trav.mask[row, col]
                if val == OBSTACLE:
                    self.grid[cy, cx] = OCC_OBSTACLE
                elif val == TRAVERSABLE:
                    if self.grid[cy, cx] != OCC_OBSTACLE:
                        self.grid[cy, cx] = FREE
                # UNKNOWN traversability leaves the existing cell value alone.

    def inflate_obstacles(self, radius_cells: int = 1) -> np.ndarray:
        """Return a copy of the grid with obstacles morphologically dilated,
        giving the planner a safety margin instead of grazing obstacle edges."""
        import cv2
        obstacle_mask = (self.grid == OCC_OBSTACLE).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius_cells * 2 + 1,) * 2)
        inflated = cv2.dilate(obstacle_mask, kernel)
        result = self.grid.copy()
        result[inflated > 0] = OCC_OBSTACLE
        return result
