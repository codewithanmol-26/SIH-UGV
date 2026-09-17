import time

from control.motor_controller import SimulationMotorController, VelocityCommand, MotionCommand
from mapping.occupancy_grid import OccupancyGrid, OCC_OBSTACLE
from simulation.simulator import UGVSimulator


def test_simulator_moves_forward_on_velocity_command():
    sim = UGVSimulator()
    mc = SimulationMotorController(sim)
    mc.send(VelocityCommand(1.0, 0.0, MotionCommand.FORWARD))
    for _ in range(5):
        sim.tick()
        time.sleep(0.02)
    assert sim.state.x > 0
    assert sim.state.distance_travelled_m > 0


def test_simulator_emergency_stop_halts_motion():
    sim = UGVSimulator()
    mc = SimulationMotorController(sim)
    mc.send(VelocityCommand(1.0, 0.0, MotionCommand.FORWARD))
    sim.tick()
    mc.emergency_stop()
    x_after_stop = sim.state.x
    for _ in range(5):
        sim.tick()
        time.sleep(0.02)
    assert abs(sim.state.x - x_after_stop) < 1e-6


def test_simulator_detects_collision_with_occupied_cell():
    sim = UGVSimulator()
    grid = OccupancyGrid(size_m=10.0, cell_size_m=0.25)
    # Place an obstacle directly on the UGV's starting cell.
    cx, cy = grid.world_to_cell(0.0, 0.0)
    grid.grid[cy, cx] = OCC_OBSTACLE
    sim.apply_velocity(0.0, 0.0)
    sim.tick(grid)  # first tick has dt=0, establishes baseline
    sim.tick(grid)
    assert sim.state.collided is True


def test_simulator_no_collision_in_open_grid():
    sim = UGVSimulator()
    grid = OccupancyGrid(size_m=10.0, cell_size_m=0.25)
    sim.apply_velocity(0.0, 0.0)
    sim.tick(grid)
    sim.tick(grid)
    assert sim.state.collided is False


def test_simulator_stops_moving_after_collision():
    sim = UGVSimulator()
    grid = OccupancyGrid(size_m=10.0, cell_size_m=0.25)
    cx, cy = grid.world_to_cell(0.2, 0.0)
    grid.grid[cy, cx] = OCC_OBSTACLE
    sim.apply_velocity(1.0, 0.0)
    for _ in range(20):
        sim.tick(grid)
        time.sleep(0.02)
        if sim.state.collided:
            break
    assert sim.state.collided is True
    x_at_collision = sim.state.x
    for _ in range(5):
        sim.tick(grid)
        time.sleep(0.02)
    assert sim.state.x == x_at_collision
