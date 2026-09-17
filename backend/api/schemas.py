from __future__ import annotations

from pydantic import BaseModel, Field


class DestinationRequest(BaseModel):
    x: float = Field(..., description="Destination X in the local coordinate frame (meters)")
    y: float = Field(..., description="Destination Y in the local coordinate frame (meters)")


class CameraSourceRequest(BaseModel):
    source: str = Field(..., description="'webcam' | 'video_file' | 'ip_stream' | 'rtsp'")


class ActionResponse(BaseModel):
    ok: bool
    state: str
    message: str = ""


class NavigationStatusResponse(BaseModel):
    state: str
    destination: tuple[float, float] | None
    plan_found: bool
    waypoints: list[tuple[float, float]]


class PositionResponse(BaseModel):
    x: float
    y: float
    heading_deg: float
    localization_confidence: float
    localization_status: str


class TelemetryResponse(BaseModel):
    x: float
    y: float
    heading_deg: float
    velocity: float
    distance_travelled_m: float
    distance_remaining_m: float | None
    obstacle_count: int
    camera_fps: float
    inference_fps: float
    ai_latency_ms: float
    localization_confidence: float


class SystemStatusResponse(BaseModel):
    state: str
    camera: str
    perception: str
    traversability: str
    localization: str
    planner: str
    controller: str
    communication: str


class DetectionResponse(BaseModel):
    cls_name: str
    confidence: float
    x: float
    y: float
    w: float
    h: float
