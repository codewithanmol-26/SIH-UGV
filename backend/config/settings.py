"""
Central configuration for the UGV navigation backend.

Everything that used to be a magic number scattered across modules lives
here instead, loaded from environment variables (see ../../.env.example)
with sane defaults so the system runs out of the box in DEVELOPMENT mode.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
MODELS_DIR = PROJECT_ROOT / "models"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="UGV_", extra="ignore")

    # --- Runtime mode -----------------------------------------------------
    # DEVELOPMENT: laptop + webcam/video file, SimulationMotorController.
    # HARDWARE:    onboard computer + real camera + HardwareMotorController.
    runtime_mode: Literal["DEVELOPMENT", "HARDWARE"] = "DEVELOPMENT"

    # --- Camera -------------------------------------------------------
    camera_source: Literal["webcam", "video_file", "ip_stream", "rtsp"] = "webcam"
    camera_device_index: int = 0
    camera_video_path: str = str(PROJECT_ROOT / "sample_data" / "sample_outdoor.mp4")
    camera_ip_url: str = ""  # e.g. http://<phone-ip>:8080/video (IP Webcam app)
    camera_rtsp_url: str = ""
    camera_width: int = 640
    camera_height: int = 480
    camera_target_fps: int = 30

    # --- AI perception --------------------------------------------------
    yolo_model_name: str = "yolo26n.pt"  # nano — swap for yolo26s.pt etc. if perf allows
    yolo_weights_path: str = str(MODELS_DIR / "yolo26n.pt")
    yolo_confidence_threshold: float = 0.45
    yolo_iou_threshold: float = 0.5
    yolo_inference_size: int = 480
    yolo_device: Literal["cpu", "cuda", "auto"] = "auto"

    # --- Traversability ---------------------------------------------------
    # "classical": geometric ground-plane / color-texture heuristic (ACTIVE now)
    # "segmentation": YOLO26-seg based mask (interface ready, NOT IMPLEMENTED yet)
    traversability_method: Literal["classical", "segmentation"] = "classical"

    # --- Localization -----------------------------------------------------
    # "orb_vo": ORB feature matching + essential-matrix motion estimate (ACTIVE)
    # "slam3": placeholder hook for a future ORB-SLAM3 integration (NOT IMPLEMENTED)
    localization_method: Literal["orb_vo", "slam3"] = "orb_vo"
    localization_min_matches: int = 25
    localization_low_confidence_threshold: float = 0.35

    # --- Mapping / planning ------------------------------------------------
    map_size_m: float = 40.0       # local map spans [-20, +20] m in x and y
    map_cell_size_m: float = 0.25  # occupancy grid resolution
    planner_replan_interval_s: float = 1.0

    # --- Motion control -----------------------------------------------------
    max_linear_velocity: float = 1.6   # m/s
    max_angular_velocity: float = 1.0  # rad/s

    # --- Safety -------------------------------------------------------------
    camera_timeout_s: float = 2.0
    safe_stop_obstacle_margin_m: float = 0.4

    # --- Server ---------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Optional persistence (disabled by default; §18 of spec) -------
    database_enabled: bool = False
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'ugv_sessions.db'}"


settings = Settings()
