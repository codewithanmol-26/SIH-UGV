# Development

## Prerequisites

- Python 3.12+ (backend was built/tested against 3.12.3)
- Node.js 22+ / npm 10+
- `ffmpeg` on PATH if you plan to generate or transcode sample video
  (not required for `webcam` mode)

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env.example .env           # optional, defaults work out of the box
python main.py
```

First run with perception enabled will download `yolo26n.pt` automatically
via ultralytics — this needs outbound internet access once; after that it's
cached under `models/`.

Interactive API docs: `http://localhost:8000/docs`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, talks to backend on :8000
```

Environment overrides (create `frontend/.env`):

```
VITE_API_BASE=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws/telemetry
```

## Running without a webcam

```bash
# backend/.env
UGV_CAMERA_SOURCE=video_file
UGV_CAMERA_VIDEO_PATH=../sample_data/sample_outdoor.mp4
```

Drop real outdoor footage at that path for a meaningful demo — the repo
intentionally does not ship large sample video (see `.gitignore`).

## Tests

```bash
# from the project root
pip install -r backend/requirements.txt pytest
pytest tests/ -v
```

39 tests across camera I/O, A* planning, the navigation state machine,
safety rules, the simulator/collision detection, and REST/WebSocket
integration (`tests/backend/`). Configuration lives in `pyproject.toml`
(`pythonpath = ["backend"]`) plus `tests/backend/conftest.py`, which points
every test at `UGV_CAMERA_SOURCE=video_file` so the suite runs
deterministically without a real webcam or GPU.

A handful of tests need a real (even tiny) video file present at
`sample_data/sample_outdoor.mp4`. Generate a throwaway one if it's missing:

```bash
ffmpeg -f lavfi -i "testsrc2=size=320x240:rate=15:duration=2" \
  -c:v libx264 -pix_fmt yuv420p sample_data/sample_outdoor.mp4
```

Frontend type-checking / build:

```bash
cd frontend
npx tsc -b --noEmit
npm run build
```

## Dependency version policy

Every pinned version in `backend/requirements.txt` and
`frontend/package.json` was checked against the live PyPI/npm registries at
the time this MVP was built — not assumed from training data. Re-verify
before a long-lived deployment:

```bash
# Python
curl -s https://pypi.org/pypi/<package>/json | python3 -c "import json,sys;print(json.load(sys.stdin)['info']['version'])"

# Node
npm view <package> dist-tags
```

Watch `torch`/`torchvision` in particular — they move fast and occasionally
desync; if the exact pinned pair fails to resolve, install `torch` first
and let pip pick a matching `torchvision`.

## Code layout conventions

- Every perception/localization/planning/control module exposes a small
  interface (`CameraSource`, `TraversabilityEstimator`,
  `LocalizationBackend`, `Planner`, `MotorController`) plus a `create_*()`
  factory keyed off `config/settings.py` — swapping an implementation
  should never require touching the orchestrator in
  `communication/state_manager.py`.
- Every such class carries a `status: ModuleStatus` class attribute
  (`ACTIVE` / `SIMULATED` / `NOT_IMPLEMENTED`, spec §30). Unimplemented
  paths raise `NotImplementedError` rather than returning plausible-looking
  fake data.
- Frontend types in `frontend/src/types/index.ts` are hand-mirrored from
  the backend's Pydantic schemas and WebSocket payload — there's no codegen
  step, so a backend field rename must be made in both places.
