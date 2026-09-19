from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.schemas import (
    ActionResponse, DestinationRequest, CameraSourceRequest,
    NavigationStatusResponse, PositionResponse, TelemetryResponse,
    SystemStatusResponse, DetectionResponse,
)

router = APIRouter()


def _nav(request: Request):
    return request.app.state.navigation_system


@router.post("/navigation/destination", response_model=ActionResponse)
async def set_destination(body: DestinationRequest, request: Request):
    nav = _nav(request)
    ok = nav.set_destination(body.x, body.y)
    return ActionResponse(ok=ok, state=nav.fsm.state.value)


@router.post("/navigation/start", response_model=ActionResponse)
async def start_navigation(request: Request):
    nav = _nav(request)
    ok = nav.start()
    if not ok:
        raise HTTPException(status_code=409, detail=f"Cannot start from state {nav.fsm.state.value}")
    return ActionResponse(ok=ok, state=nav.fsm.state.value)


@router.post("/navigation/pause", response_model=ActionResponse)
async def pause_navigation(request: Request):
    nav = _nav(request)
    ok = nav.pause()
    return ActionResponse(ok=ok, state=nav.fsm.state.value)


@router.post("/navigation/resume", response_model=ActionResponse)
async def resume_navigation(request: Request):
    nav = _nav(request)
    ok = nav.resume()
    return ActionResponse(ok=ok, state=nav.fsm.state.value)


@router.post("/navigation/stop", response_model=ActionResponse)
async def stop_navigation(request: Request):
    nav = _nav(request)
    ok = nav.stop()
    return ActionResponse(ok=ok, state=nav.fsm.state.value)


@router.post("/navigation/emergency-stop", response_model=ActionResponse)
async def emergency_stop(request: Request):
    nav = _nav(request)
    ok = nav.emergency_stop()
    return ActionResponse(ok=ok, state=nav.fsm.state.value, message="Emergency stop engaged")


@router.get("/navigation/status", response_model=NavigationStatusResponse)
async def navigation_status(request: Request):
    nav = _nav(request)
    plan = nav.current_plan
    return NavigationStatusResponse(
        state=nav.fsm.state.value,
        destination=nav.destination,
        plan_found=bool(plan and plan.found),
        waypoints=plan.waypoints_world if plan else [],
    )


@router.get("/ugv/position", response_model=PositionResponse)
async def ugv_position(request: Request):
    nav = _nav(request)
    pose = nav.latest_pose
    return PositionResponse(
        x=pose.x if pose else nav.simulator.state.x,
        y=pose.y if pose else nav.simulator.state.y,
        heading_deg=pose.heading_deg if pose else nav.simulator.state.heading_deg,
        localization_confidence=pose.confidence if pose else 0.0,
        localization_status=nav.status.localization.value,
    )


@router.get("/ugv/telemetry", response_model=TelemetryResponse)
async def ugv_telemetry(request: Request):
    nav = _nav(request)
    t = nav.telemetry
    return TelemetryResponse(**t.__dict__)


@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status(request: Request):
    nav = _nav(request)
    s = nav.status
    return SystemStatusResponse(
        state=nav.fsm.state.value,
        camera=s.camera.value,
        perception=s.perception.value,
        traversability=s.traversability.value,
        localization=s.localization.value,
        planner=s.planner.value,
        controller=s.controller.value,
        communication=s.communication.value,
    )


@router.get("/perception/objects", response_model=list[DetectionResponse])
async def perception_objects(request: Request):
    nav = _nav(request)
    result = nav.latest_detections
    if result is None:
        return []
    return [
        DetectionResponse(cls_name=d.cls_name, confidence=d.confidence, x=d.x, y=d.y, w=d.w, h=d.h)
        for d in result.detections
    ]


@router.post("/camera/source", response_model=ActionResponse)
async def set_camera_source(body: CameraSourceRequest, request: Request):
    # Switching the live source safely requires re-running initialize();
    # exposed as a documented limitation rather than half-implemented here.
    raise HTTPException(
        status_code=501,
        detail=(
            "Hot-swapping camera source at runtime is not implemented in this MVP. "
            "Set UGV_CAMERA_SOURCE in .env and restart the backend."
        ),
    )
