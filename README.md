# UGV Mission Console

Vision-based autonomous navigation MVP for **Smart India Hackathon Problem
Statement 26126** — *Vision Based Autonomous Navigation for Unmanned Ground
Vehicle for Outdoor Environment*.

An outdoor UGV navigating a GPS-denied environment using camera-based
perception as its primary sense: detect obstacles, work out where the
ground is actually driveable, estimate its own motion from the camera feed,
plan a path to an operator-chosen destination, and replan the moment
something steps into the way — all runnable on a laptop with a webcam,
with the same architecture meant to move onto a Jetson/Raspberry Pi later.

## Problem statement

| | |
|---|---|
| **ID** | 26126 |
| **Core requirements** | 1) Path / traversable-area detection · 2) Visual localization / visual odometry · 3) Dynamic collision avoidance and path planning |
| **Constraint** | Must run on a laptop (webcam / recorded video) with zero UGV hardware, and be transferable later to an onboard Jetson/Raspberry Pi/Linux computer |

## Honesty labels

Every module reports one of three statuses, both in the code and on the
dashboard's STATUS panel, so nobody mistakes a placeholder for a working
algorithm:

| Label | Meaning |
|---|---|
| **ACTIVE** | Real algorithm, real output, running against real (or real-recorded) camera frames |
| **SIMULATED** | Standing in for hardware that doesn't exist yet (the UGV simulator, its motor controller) — the computation is real, the *chassis* is not |
| **NOT_IMPLEMENTED** | Interface exists so it can be filled in later; calling it raises rather than silently faking a result |

Current status of every module:

| Module | Status | Notes |
|---|---|---|
| Camera — webcam | **ACTIVE** | `cv2.VideoCapture` against a device index |
| Camera — video file | **ACTIVE** | Loops automatically past EOF |
| Camera — IP/RTSP stream | NOT_IMPLEMENTED | Interface only — see `backend/perception/camera.py` |
| Obstacle detection (YOLO26) | **ACTIVE** | Ultralytics YOLO26, nano weights auto-downloaded on first run |
| Traversability (classical CV) | **ACTIVE** | Ground-plane color/texture heuristic, not learned segmentation |
| Traversability (segmentation) | NOT_IMPLEMENTED | Interface reserved for `yolo26-seg` or similar |
| Visual localization (ORB VO) | **ACTIVE** | Monocular, relative-scale — see limitations below |
| Localization (SLAM3) | NOT_IMPLEMENTED | Interface reserved for ORB-SLAM3 / VIO / stereo depth |
| Local map / occupancy grid | **ACTIVE** | Flat-ground projection, near-field only |
| Path planner (A*) | **ACTIVE** | 8-connected grid search with obstacle inflation |
| Dynamic replanning | **ACTIVE** | Blocked-route detection triggers a fresh A* plan every tick |
| UGV simulator | **SIMULATED** | Real kinematics/collision checks, simulated chassis |
| Motor controller — simulation | **SIMULATED** | Drives the simulator from real velocity commands |
| Motor controller — hardware | NOT_IMPLEMENTED | No physical driver wired up — see `docs/hardware-integration.md` |
| Safety monitor | **ACTIVE** | Camera-loss / low-confidence / no-path / e-stop rules |
| WebSocket telemetry | **ACTIVE** | ~6-7Hz, includes the camera frame with overlay |

## Architecture

```
CAMERA → VIDEO INPUT LAYER → AI PERCEPTION
                                  │
                  ┌───────────────┴────────────────┐
                  ▼                                 ▼
          Obstacle Detection             Traversable Area Detection
                  └───────────────┬────────────────┘
                                  ▼
                        VISUAL LOCALIZATION
                                  ▼
                             LOCAL MAP
                                  ▼
                            PATH PLANNER
                                  ▼
                       COLLISION AVOIDANCE
                                  ▼
                          MOTION CONTROL
                                  ▼
                       UGV / SIMULATOR

         UGV / BACKEND  ⇄  WebSocket / REST  ⇄  OPERATOR DASHBOARD
```

The browser is an operator console, never the autonomous brain — every
decision above the motor-command level happens in the Python backend. See
`docs/architecture.md` for the full module breakdown.

## Technology stack

| Layer | Stack |
|---|---|
| Frontend | React 19.3, TypeScript 7.0, Vite 8.3, Tailwind CSS 4.3 |
| Backend | Python 3.12, FastAPI 0.141, Pydantic 2.13, WebSockets |
| Computer vision | OpenCV 5.0, NumPy 2.5 |
| AI | Ultralytics YOLO26 (nano weights by default) |

All versions were checked against PyPI/npm at build time — see
`backend/requirements.txt` / `frontend/package.json` for exact pins and
`docs/development.md` for how to re-verify them.

## Quick start (development mode — laptop + webcam)

```bash
# 1. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # optional — defaults already work
python main.py             # -> http://localhost:8000, first run downloads yolo26n.pt

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                # -> http://localhost:5173
```

Open `http://localhost:5173`, wait for the camera feed to appear, click the
map to set a destination, press **START**. No webcam handy? Set
`UGV_CAMERA_SOURCE=video_file` in `backend/.env` and drop a clip at
`sample_data/sample_outdoor.mp4` (a tiny synthetic placeholder ships in that
folder purely for the test suite — swap in real outdoor footage for a real
demo).

Or with Docker (see the caveats about webcam passthrough at the top of
`docker-compose.yml`):

```bash
docker compose up --build
```

## Limitations (read before demoing)

- **Monocular visual odometry has no absolute scale.** `backend/localization/visual_odometry.py`
  assumes a fixed pixel-motion-to-meters calibration constant. Position drifts
  over time with no loop closure — this is dead-reckoning, not survey-grade
  positioning, and the dashboard's LOCALIZATION CONFIDENCE readout exists
  specifically so the operator can see when to distrust it.
- **Traversability is a color/texture heuristic**, not learned segmentation.
  It will misclassify shadowed grass, wet rock, unusual terrain colors.
- **No physical distance is ever claimed from a bounding box.** Detection
  output only carries image-pixel position, per the spec's explicit
  requirement not to fake monocular depth.
- **This is a hackathon MVP, not a certified safety system.** The safety
  rules in `backend/safety/safety_monitor.py` cover the failure modes in
  spec §19 but have not been validated against any functional-safety
  standard.

## Repository layout

```
project/
├── frontend/          React + TypeScript + Vite dashboard
├── backend/            FastAPI navigation backend
├── tests/backend/       pytest suite (39 tests — camera, planner, safety, simulator, API, ...)
├── docs/                 architecture.md, api.md, hardware-integration.md, navigation.md, development.md
├── scripts/              setup/dev helper scripts
├── sample_data/           placeholder for recorded video used in DEVELOPMENT mode
├── models/                YOLO weights land here (auto-downloaded, gitignored)
├── .env.example
└── docker-compose.yml
```

## Further reading

- [`docs/architecture.md`](docs/architecture.md) — module-by-module design
- [`docs/api.md`](docs/api.md) — REST endpoints + WebSocket protocol
- [`docs/navigation.md`](docs/navigation.md) — state machine, planner, safety rules
- [`docs/hardware-integration.md`](docs/hardware-integration.md) — what changes to run on a real UGV
- [`docs/development.md`](docs/development.md) — local setup, testing, dependency policy
