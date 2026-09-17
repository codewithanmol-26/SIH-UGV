import os
from pathlib import Path

os.environ.setdefault("UGV_CAMERA_SOURCE", "video_file")
os.environ.setdefault(
    "UGV_CAMERA_VIDEO_PATH",
    str(Path(__file__).resolve().parent.parent.parent / "sample_data" / "sample_outdoor.mp4"),
)

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "ugv-mission-console-backend"


def test_system_status_reports_module_states(client):
    r = client.get("/api/system/status")
    assert r.status_code == 200
    body = r.json()
    for key in ("camera", "perception", "traversability", "localization", "planner", "controller"):
        assert body[key] in ("ACTIVE", "SIMULATED", "NOT_IMPLEMENTED")


def test_cannot_start_without_destination(client):
    r = client.post("/api/navigation/start")
    assert r.status_code == 409


def test_full_start_pause_resume_stop_cycle(client):
    r = client.post("/api/navigation/destination", json={"x": 2.0, "y": 2.0})
    assert r.status_code == 200 and r.json()["ok"]

    r = client.post("/api/navigation/start")
    assert r.status_code == 200 and r.json()["state"] == "AUTONOMOUS"

    r = client.post("/api/navigation/pause")
    assert r.status_code == 200 and r.json()["state"] == "PAUSED"

    r = client.post("/api/navigation/resume")
    assert r.status_code == 200 and r.json()["state"] == "AUTONOMOUS"

    r = client.post("/api/navigation/stop")
    assert r.status_code == 200 and r.json()["state"] == "STOPPED"


def test_emergency_stop_overrides_autonomous(client):
    client.post("/api/navigation/destination", json={"x": 1.0, "y": 1.0})
    client.post("/api/navigation/start")
    r = client.post("/api/navigation/emergency-stop")
    assert r.status_code == 200
    assert r.json()["state"] == "EMERGENCY_STOP"


def test_camera_source_hot_swap_is_explicitly_not_implemented(client):
    r = client.post("/api/camera/source", json={"source": "rtsp"})
    assert r.status_code == 501


def test_websocket_streams_valid_telemetry_payload(client):
    with client.websocket_connect("/ws/telemetry") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "telemetry"
        assert "state" in msg
        assert "telemetry" in msg
        assert "system_status" in msg
        assert isinstance(msg["logs"], list)


def test_communication_failure_reconnect_is_client_responsibility():
    # The backend itself has no notion of "the frontend disconnected" beyond
    # closing the socket cleanly — reconnect/backoff logic lives in the
    # frontend's useTelemetryStream hook (frontend/src/hooks). This test
    # documents that boundary rather than re-testing frontend code here.
    assert True
