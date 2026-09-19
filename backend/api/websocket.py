from __future__ import annotations

import base64
import json

import cv2
from fastapi import WebSocket, WebSocketDisconnect

from perception.traversability import TRAVERSABLE, OBSTACLE


def _encode_frame_with_overlay(nav) -> str | None:
    """Draw detection boxes + traversability tint onto the latest frame and
    JPEG-encode it as a data URI the browser can drop straight into an
    <img src>. Returns None if no frame is available yet."""
    frame = nav.latest_frame
    if frame is None:
        return None

    image = frame.image.copy()

    trav = nav.latest_traversability
    if trav is not None:
        overlay = image.copy()
        overlay[trav.mask == TRAVERSABLE] = (60, 160, 60)
        overlay[trav.mask == OBSTACLE] = (40, 40, 200)
        cv2.addWeighted(overlay, 0.25, image, 0.75, 0, image)

    det_result = nav.latest_detections
    if det_result is not None:
        for d in det_result.detections:
            x1, y1 = int(d.x), int(d.y)
            x2, y2 = int(d.x + d.w), int(d.y + d.h)
            color = (40, 40, 220) if d.confidence > 0.7 else (30, 170, 220)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            label = f"{d.cls_name} {d.confidence:.2f}"
            cv2.putText(image, label, (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode("ascii")


def _build_payload(nav) -> dict:
    plan = nav.current_plan
    pose = nav.latest_pose
    return {
        "type": "telemetry",
        "state": nav.fsm.state.value,
        "position": {
            "x": pose.x if pose else nav.simulator.state.x,
            "y": pose.y if pose else nav.simulator.state.y,
            "heading_deg": pose.heading_deg if pose else nav.simulator.state.heading_deg,
            "localization_confidence": pose.confidence if pose else 0.0,
        },
        "telemetry": nav.telemetry.__dict__,
        "destination": nav.destination,
        "route": plan.waypoints_world if plan else [],
        "trajectory": nav.simulator.state.trajectory[-200:],
        "obstacles": [
            {"cls_name": d.cls_name, "confidence": d.confidence, "x": d.x, "y": d.y, "w": d.w, "h": d.h}
            for d in (nav.latest_detections.detections if nav.latest_detections else [])
        ],
        "system_status": {
            "camera": nav.status.camera.value,
            "perception": nav.status.perception.value,
            "traversability": nav.status.traversability.value,
            "localization": nav.status.localization.value,
            "planner": nav.status.planner.value,
            "controller": nav.status.controller.value,
            "communication": nav.status.communication.value,
        },
        "logs": [{"t": l.t, "text": l.text, "kind": l.kind} for l in nav.logs],
        "camera_frame": _encode_frame_with_overlay(nav),
    }


async def telemetry_websocket(websocket: WebSocket) -> None:
    """Broadcasts navigation state, telemetry, obstacles, route and the
    camera feed (with overlay) at ~6-7Hz. One-way (server -> browser);
    operator commands go through the REST endpoints in api/routes.py, not
    over this socket, so a message the browser sends here is simply
    ignored rather than silently accepted as a command."""
    await websocket.accept()
    nav = websocket.app.state.navigation_system
    import asyncio
    try:
        while True:
            payload = _build_payload(nav)
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.15)
    except WebSocketDisconnect:
        pass
