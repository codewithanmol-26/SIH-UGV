"""
Central state (spec §14) + the pipeline that runs every tick:

    camera -> detector -> traversability -> occupancy grid
           -> visual odometry -> A* planner -> safety monitor
           -> motor controller -> simulator

This is the one place that owns the NavigationState machine and the
in-memory system state the API/WebSocket layer reads from. No database is
required (spec §18) — everything here is process memory, which is also why
the whole system resets to IDLE on restart.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from config.settings import settings
from config.status_labels import ModuleStatus, NavigationState, VALID_TRANSITIONS
from perception.camera import CameraSource, Frame, create_camera_source
from perception.detector import ObstacleDetector, DetectionResult
from perception.traversability import create_traversability_estimator, TraversabilityResult
from localization.visual_odometry import create_localization_backend, Pose
from mapping.occupancy_grid import OccupancyGrid
from planning.astar import create_planner, PlanResult
from control.motor_controller import create_motor_controller, VelocityCommand, MotionCommand
from safety.safety_monitor import SafetyMonitor, SafetyVerdict
from simulation.simulator import UGVSimulator


@dataclass
class SystemStatus:
    camera: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    perception: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    traversability: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    localization: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    planner: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    controller: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    communication: ModuleStatus = ModuleStatus.ACTIVE


@dataclass
class Telemetry:
    x: float = 0.0
    y: float = 0.0
    heading_deg: float = 0.0
    velocity: float = 0.0
    distance_travelled_m: float = 0.0
    distance_remaining_m: float | None = None
    obstacle_count: int = 0
    camera_fps: float = 0.0
    inference_fps: float = 0.0
    ai_latency_ms: float = 0.0
    localization_confidence: float = 0.0


class NavigationStateMachine:
    def __init__(self) -> None:
        self.state = NavigationState.IDLE

    def can_transition(self, to_state: NavigationState) -> bool:
        if to_state == NavigationState.EMERGENCY_STOP:
            return True
        return to_state in VALID_TRANSITIONS.get(self.state, set())

    def transition(self, to_state: NavigationState) -> bool:
        if not self.can_transition(to_state):
            return False
        self.state = to_state
        return True


@dataclass
class LogEntry:
    t: str
    text: str
    kind: str = ""


class NavigationSystem:
    """The single orchestrator instance created in main.py and shared by the
    REST routes, the WebSocket broadcaster, and the background tick loop."""

    def __init__(self) -> None:
        self.fsm = NavigationStateMachine()
        self.status = SystemStatus()
        self.telemetry = Telemetry()
        self.logs: list[LogEntry] = []

        self.camera: CameraSource | None = None
        self.detector = ObstacleDetector()
        self.traversability_estimator = create_traversability_estimator(settings.traversability_method)
        self.localization_backend = create_localization_backend(
            settings.localization_method, settings.localization_min_matches,
            settings.localization_low_confidence_threshold,
        )
        self.grid = OccupancyGrid(settings.map_size_m, settings.map_cell_size_m)
        self.planner = create_planner("astar")
        self.simulator = UGVSimulator()
        self.motor_controller = create_motor_controller(settings.runtime_mode, self.simulator)
        self.safety_monitor = SafetyMonitor(
            settings.camera_timeout_s,
            settings.localization_low_confidence_threshold,
        )

        self.destination: tuple[float, float] | None = None
        self.current_plan: PlanResult | None = None
        self.emergency_stop_requested = False
        self._last_replan_time = 0.0

        self.latest_frame: Frame | None = None
        self.latest_detections: DetectionResult | None = None
        self.latest_traversability: TraversabilityResult | None = None
        self.latest_pose: Pose | None = None

        self._fps_window: list[float] = []
        self._inference_fps_window: list[float] = []

        self._lock = asyncio.Lock()
        self._running = False

    # ---- logging -----------------------------------------------------
    def log(self, text: str, kind: str = "") -> None:
        entry = LogEntry(t=time.strftime("%H:%M:%S"), text=text, kind=kind)
        self.logs.insert(0, entry)
        self.logs = self.logs[:12]

    # ---- lifecycle -----------------------------------------------------
    async def initialize(self) -> None:
        self.fsm.transition(NavigationState.INITIALIZING)
        self.log("System initializing", "")

        self.camera = create_camera_source(settings.camera_source, settings)
        opened = self.camera.open()
        self.status.camera = self.camera.status if opened else ModuleStatus.NOT_IMPLEMENTED

        if not opened:
            self.log(f"Camera source '{settings.camera_source}' failed to open", "flag")
            self.fsm.transition(NavigationState.ERROR)
            return

        try:
            self.detector.load()
            self.status.perception = ModuleStatus.ACTIVE
        except Exception as exc:  # model download/load failure shouldn't crash the server
            self.log(f"YOLO model failed to load: {exc}", "flag")
            self.status.perception = ModuleStatus.NOT_IMPLEMENTED

        self.status.traversability = self.traversability_estimator.status
        self.status.localization = self.localization_backend.status
        self.status.planner = self.planner.status
        self.status.controller = self.motor_controller.status

        self.simulator.reset()
        self.localization_backend.reset()

        self.fsm.transition(NavigationState.READY)
        self.log("System ready", "good")

    # ---- operator commands -----------------------------------------------------
    def set_destination(self, x: float, y: float) -> bool:
        self.destination = (x, y)
        self.log(f"Destination set to ({x:.1f}, {y:.1f})", "")
        return True

    def start(self) -> bool:
        if self.destination is None:
            self.log("Cannot start — no destination set", "flag")
            return False
        ok = self.fsm.transition(NavigationState.AUTONOMOUS)
        if ok:
            self.log("Navigation started — AUTONOMOUS", "good")
        return ok

    def pause(self) -> bool:
        ok = self.fsm.transition(NavigationState.PAUSED)
        if ok:
            self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
            self.log("Navigation paused", "")
        return ok

    def resume(self) -> bool:
        ok = self.fsm.transition(NavigationState.AUTONOMOUS)
        if ok:
            self.log("Navigation resumed", "good")
        return ok

    def stop(self) -> bool:
        ok = self.fsm.transition(NavigationState.STOPPED)
        self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
        self.destination = None
        self.current_plan = None
        self.log("Navigation stopped", "")
        return ok

    def emergency_stop(self) -> bool:
        self.emergency_stop_requested = True
        self.fsm.transition(NavigationState.EMERGENCY_STOP)
        self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
        self.log("EMERGENCY STOP triggered", "flag")
        return True

    def clear_emergency_stop(self) -> bool:
        self.emergency_stop_requested = False
        ok = self.fsm.transition(NavigationState.STOPPED)
        if ok:
            self.log("Emergency stop cleared — system STOPPED, re-init required to resume", "good")
        return ok

    # ---- main tick -----------------------------------------------------
    async def tick(self) -> None:
        async with self._lock:
            frame = self.camera.read() if self.camera else None
            camera_stale = self.camera.is_stale(settings.camera_timeout_s) if self.camera else True

            if frame is not None:
                self.latest_frame = frame
                self._fps_window.append(frame.timestamp)
                self._fps_window = [t for t in self._fps_window if frame.timestamp - t <= 2.0]
                self.telemetry.camera_fps = round(len(self._fps_window) / 2.0, 1)

                det_result = self.detector.infer(frame.image) if self.status.perception == ModuleStatus.ACTIVE else DetectionResult()
                self.latest_detections = det_result
                self.telemetry.ai_latency_ms = det_result.inference_ms
                self.telemetry.obstacle_count = len(det_result.detections)
                if det_result.inference_ms > 0:
                    self._inference_fps_window.append(time.monotonic())
                    self._inference_fps_window = [t for t in self._inference_fps_window if time.monotonic() - t <= 2.0]
                    self.telemetry.inference_fps = round(len(self._inference_fps_window) / 2.0, 1)

                trav_result = self.traversability_estimator.estimate(frame.image, det_result.detections)
                self.latest_traversability = trav_result

                pose = self.localization_backend.update(frame.image)
                self.latest_pose = pose
                self.telemetry.localization_confidence = pose.confidence

                if self.fsm.state in (NavigationState.AUTONOMOUS, NavigationState.REROUTING):
                    self.grid.update_from_traversability(trav_result, pose.x, pose.y, pose.heading_deg)

            self._run_safety_and_control(camera_stale)
            self._update_telemetry_from_sim()

    def _run_safety_and_control(self, camera_stale: bool) -> None:
        verdict = self.safety_monitor.check(
            system_initialized=self.status.perception != ModuleStatus.NOT_IMPLEMENTED,
            camera_is_stale=camera_stale,
            localization_confidence=self.telemetry.localization_confidence,
            planner_found_path=(self.current_plan.found if self.current_plan else True),
            emergency_stop_requested=self.emergency_stop_requested,
            current_state=self.fsm.state,
        )

        if verdict.verdict == SafetyVerdict.BLOCK_MOVEMENT:
            self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
            return

        if verdict.verdict == SafetyVerdict.SAFE_STOP and self.fsm.state in (
            NavigationState.AUTONOMOUS, NavigationState.REROUTING,
        ):
            self.fsm.transition(NavigationState.SAFE_STOP)
            self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
            self.log(f"SAFE_STOP — {verdict.reason}", "flag")
            return

        if self.fsm.state not in (NavigationState.AUTONOMOUS, NavigationState.REROUTING):
            self.simulator.tick(self.grid)
            return

        self._navigate_step()

    def _navigate_step(self) -> None:
        if self.destination is None or self.latest_pose is None:
            return

        pose = self.latest_pose
        now = time.monotonic()
        need_replan = (
            self.current_plan is None
            or not self.current_plan.found
            or (now - self._last_replan_time) > settings.planner_replan_interval_s
        )

        blocked = self._plan_is_blocked()
        if blocked and self.fsm.state == NavigationState.AUTONOMOUS:
            self.fsm.transition(NavigationState.REROUTING)
            self.log("Path blocked — rerouting", "flag")
            need_replan = True

        if need_replan:
            self._last_replan_time = now
            self.current_plan = self.planner.plan(self.grid, (pose.x, pose.y), self.destination)
            if self.current_plan.found:
                if self.fsm.state == NavigationState.REROUTING:
                    self.fsm.transition(NavigationState.AUTONOMOUS)
                    self.log("New route computed, resuming", "good")
            else:
                self.fsm.transition(NavigationState.SAFE_STOP)
                self.log("No safe path found — SAFE_STOP", "flag")
                self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
                self.simulator.tick(self.grid)
                return

        dist_to_dest = self.simulator.distance_to(*self.destination)
        self.telemetry.distance_remaining_m = round(dist_to_dest, 2)
        if dist_to_dest < 0.6:
            self.fsm.transition(NavigationState.DESTINATION_REACHED)
            self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
            self.log("Destination reached", "good")
            self.simulator.tick(self.grid)
            return

        velocity = self._compute_velocity_command(pose)
        self.motor_controller.send(velocity)
        self.simulator.tick(self.grid)

        if self.simulator.state.collided:
            self.fsm.transition(NavigationState.SAFE_STOP)
            self.motor_controller.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))
            self.log("Collision detected in simulation — SAFE_STOP", "flag")

    def _plan_is_blocked(self) -> bool:
        if self.current_plan is None or not self.current_plan.found:
            return False
        from mapping.occupancy_grid import OCC_OBSTACLE
        for (wx, wy) in self.current_plan.waypoints_world:
            cx, cy = self.grid.world_to_cell(wx, wy)
            if self.grid.in_bounds(cx, cy) and self.grid.grid[cy, cx] == OCC_OBSTACLE:
                return True
        return False

    def _compute_velocity_command(self, pose: Pose) -> VelocityCommand:
        import numpy as np
        if not self.current_plan or not self.current_plan.waypoints_world:
            return VelocityCommand(0.0, 0.0, MotionCommand.STOP)

        target_x, target_y = self.current_plan.waypoints_world[
            min(1, len(self.current_plan.waypoints_world) - 1)
        ]
        dx, dy = target_x - self.simulator.state.x, target_y - self.simulator.state.y
        target_heading = np.degrees(np.arctan2(dy, dx))
        heading_error = ((target_heading - self.simulator.state.heading_deg + 180) % 360) - 180

        angular = np.clip(np.radians(heading_error) * 1.2, -settings.max_angular_velocity, settings.max_angular_velocity)
        # Slow down for sharp turns rather than driving blind through them.
        linear = settings.max_linear_velocity * max(0.15, 1 - abs(heading_error) / 90)
        linear = min(linear, settings.max_linear_velocity)

        cmd = MotionCommand.FORWARD if abs(heading_error) < 45 else (
            MotionCommand.TURN_LEFT if heading_error > 0 else MotionCommand.TURN_RIGHT
        )
        return VelocityCommand(float(linear), float(angular), cmd)

    def _update_telemetry_from_sim(self) -> None:
        s = self.simulator.state
        self.telemetry.x = s.x
        self.telemetry.y = s.y
        self.telemetry.heading_deg = s.heading_deg
        self.telemetry.velocity = s.linear_velocity
        self.telemetry.distance_travelled_m = round(s.distance_travelled_m, 2)

    # ---- background loop -----------------------------------------------------
    async def run_forever(self, hz: float = 10.0) -> None:
        self._running = True
        interval = 1.0 / hz
        while self._running:
            t0 = time.monotonic()
            try:
                await self.tick()
            except Exception as exc:  # keep the loop alive; surface the error via logs/state
                self.log(f"Tick error: {exc}", "flag")
                self.fsm.transition(NavigationState.ERROR)
            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0.0, interval - elapsed))

    def stop_loop(self) -> None:
        self._running = False
        if self.camera:
            self.camera.release()
