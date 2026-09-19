# Architecture

## Pipeline

```
CAMERA (webcam / video file)
    │
    ▼
CameraSource.read()  →  Frame(image, timestamp, frame_index)
    │
    ▼
ObstacleDetector.infer()  →  DetectionResult (YOLO26, ACTIVE)
    │
    ▼
TraversabilityEstimator.estimate()  →  TraversabilityResult (classical CV, ACTIVE)
    │
    ├──────────────────────────────┐
    ▼                              ▼
LocalizationBackend.update()   OccupancyGrid.update_from_traversability()
  → Pose (x, y, heading,         (only while AUTONOMOUS/REROUTING)
     confidence — ORB VO, ACTIVE)
    │                              │
    └──────────────┬───────────────┘
                    ▼
            Planner.plan()  →  PlanResult (A*, ACTIVE)
                    ▼
          SafetyMonitor.check()  →  SafetyVerdict
                    ▼
        MotorController.send()  →  VelocityCommand
                    ▼
             UGVSimulator.tick()  (SIMULATED chassis, real kinematics)
```

All of this runs inside `NavigationSystem.tick()`
(`backend/communication/state_manager.py`), called at 10Hz by
`NavigationSystem.run_forever()`, which FastAPI's `lifespan` starts as a
background `asyncio` task in `backend/main.py`. One tick, one pass through
the whole pipeline, one `async with self._lock` so the REST endpoints (which
mutate `destination`, `emergency_stop_requested`, etc.) never race the loop.

## Why each module is where it is

**`perception/camera.py`** — `CameraSource` is the only thing anything else
in the pipeline depends on. `WebcamSource` and `VideoFileSource` share an
implementation (`_OpenCVCaptureSource`) since both are just
`cv2.VideoCapture` under the hood; `IPStreamSource`/`RTSPSource` reuse the
exact same mechanism but are labelled `NOT_IMPLEMENTED` until tested against
a real stream — the honest thing to do given the code path is identical but
unverified.

**`perception/detector.py`** — wraps `ultralytics.YOLO` but returns plain
`Detection` dataclasses. Nothing downstream imports `ultralytics` directly,
so swapping YOLO26 for a future model means editing this one file.

**`perception/traversability.py`** — the classical-CV estimator samples a
trapezoid of "known ground" at the bottom of the frame, builds an HSV color
histogram, and back-projects it across the whole image. YOLO detections
always override the color heuristic (an obstacle box is `OBSTACLE`
regardless of what color it is). `SegmentationTraversabilityEstimator` is a
stub that raises `NotImplementedError` — it exists so the planner's
`TraversabilityResult` contract never has to change when a real segmentation
model replaces the heuristic.

**`localization/visual_odometry.py`** — ORB feature detection +
Hamming-distance matching + `cv2.findEssentialMat`/`recoverPose` for
frame-to-frame rotation and translation *direction*. Monocular geometry
can't recover absolute translation scale, so a calibration constant
(`_ASSUMED_SCALE_M`) stands in for it — documented in the module docstring,
not hidden. `confidence` comes from match count, and the safety monitor acts
on it directly.

**`mapping/occupancy_grid.py`** — a square grid centered on the UGV's start
position (no GPS, so "world" coordinates are relative to wherever the UGV
was powered on). `update_from_traversability` projects the near-field rows
of the traversability mask onto the ground plane using a flat-ground, fixed-
camera-pitch assumption — deliberately only the bottom ~40% of the frame,
where that assumption is least wrong.

**`planning/astar.py`** — 8-connected A* over `OccupancyGrid.inflate_obstacles()`
(a dilated copy of the grid, so the planner keeps a margin instead of
grazing obstacle edges). `UNKNOWN` cells are passable but cost 3x more than
`FREE` cells, so the UGV prefers known-clear ground but isn't paralyzed by
not having seen every patch yet.

**`control/motor_controller.py`** / **`simulation/simulator.py`** — the
motor controller never touches simulator internals beyond
`apply_velocity()`; the simulator never knows a motor controller exists. A
real `HardwareMotorController` slots in by implementing `send()` for an
actual driver — nothing else in the pipeline changes.

**`safety/safety_monitor.py`** — pure veto power. It never decides *what*
the UGV should do, only whether the current tick is allowed to move at all.
`communication/state_manager.py` calls it every tick before acting on the
planner's output.

**`communication/state_manager.py`** — the one place that owns
`NavigationState` and in-memory system state. No database, per spec §18 —
restart the process and you're back to `IDLE`.

## Frontend architecture

```
useTelemetryStream()  →  TelemetryMessage (WebSocket, ~150ms)
        │
        ▼
   Dashboard.tsx  (owns pendingDestination / busy / error UI state)
        │
        ├── MapPanel        (click-to-set Point B, trajectory, route)
        ├── CameraPanel      (live frame + detection/traversability overlay)
        ├── ControlPanel      (START/PAUSE/RESUME/STOP/E-STOP → REST calls)
        ├── StatusPanel        (per-module ACTIVE/SIMULATED/NOT_IMPLEMENTED)
        ├── TelemetryPanel      (X/Y/heading/velocity/distances/confidence)
        └── LogPanel              (event log)
```

One WebSocket connection, one hook, one source of truth — every panel reads
from the same `TelemetryMessage` rather than opening its own socket or
polling REST endpoints for live data. Operator *commands* (start/pause/
destination/etc.) go over REST (`services/api.ts`), never over the
WebSocket, which is intentionally one-way (server → browser).

## Local coordinate frame, not GPS

There is no GPS anywhere in this system by design (spec constraint: GPS-
denied environment). "World" coordinates (`x`, `y` in meters) are relative
to wherever the UGV was powered on — `(0, 0)` — with heading in degrees.
Point A is always the origin; Point B is whatever the operator clicks on the
map, converted from screen pixels to that same local frame
(`MapPanel.toWorld`).
