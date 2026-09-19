import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Use a lightweight, deterministic config for every test in this session.
os.environ.setdefault("UGV_CAMERA_SOURCE", "video_file")
os.environ.setdefault("UGV_CAMERA_VIDEO_PATH", str(PROJECT_ROOT / "sample_data" / "sample_outdoor.mp4"))
