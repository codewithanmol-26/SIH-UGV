import numpy as np

from mapping.occupancy_grid import OccupancyGrid, OCC_OBSTACLE, FREE
from planning.astar import AStarPlanner


def _open_grid(size=20.0, cell=0.25):
    grid = OccupancyGrid(size, cell)
    grid.grid[:, :] = FREE
    return grid


def test_astar_clear_path():
    grid = _open_grid()
    planner = AStarPlanner()
    result = planner.plan(grid, (0.0, 0.0), (5.0, 0.0))
    assert result.found
    assert len(result.waypoints_world) >= 2
    assert result.waypoints_world[0] == (0.0, 0.0)


def test_astar_routes_around_single_obstacle():
    grid = _open_grid()
    # Wall obstacle directly between start and goal along y=0, with no gap.
    cx0, cy0 = grid.world_to_cell(2.0, 0.0)
    for dy in range(-8, 9):
        grid.grid[cy0 + dy, cx0] = OCC_OBSTACLE
    planner = AStarPlanner()
    result = planner.plan(grid, (0.0, 0.0), (5.0, 0.0))
    assert result.found
    # The path must deviate from a straight line (go around, not through).
    ys = [wy for _, wy in result.waypoints_world]
    assert max(abs(y) for y in ys) > 0.5


def test_astar_blocked_route_returns_not_found():
    grid = _open_grid(size_m := 10.0, cell=0.5)
    del size_m
    cx0, cy0 = grid.world_to_cell(2.0, 0.0)
    n = grid.n_cells
    for row in range(n):
        grid.grid[row, cx0] = OCC_OBSTACLE  # solid wall, no gap, spans full grid height
    planner = AStarPlanner()
    result = planner.plan(grid, (0.0, 0.0), (4.0, 0.0))
    assert not result.found
    assert result.waypoints_world == []


def test_world_to_cell_roundtrip():
    grid = OccupancyGrid(20.0, 0.25)
    x, y = grid.cell_to_world(*grid.world_to_cell(3.25, -1.5))
    assert abs(x - 3.25) < 1e-6
    assert abs(y - (-1.5)) < 1e-6


def test_inflate_obstacles_grows_footprint():
    grid = _open_grid()
    cx, cy = grid.world_to_cell(0, 0)
    grid.grid[cy, cx] = OCC_OBSTACLE
    inflated = grid.inflate_obstacles(radius_cells=2)
    assert inflated[cy, cx + 1] == OCC_OBSTACLE
    assert np.sum(inflated == OCC_OBSTACLE) > 1
