# Hardware Integration

This MVP runs entirely on a laptop by design (spec §21). This document is
the checklist for what actually changes to run on a physical UGV — the
point of the architecture is that it's a short list.

## What does *not* change

- `perception/detector.py`, `perception/traversability.py`,
  `localization/visual_odometry.py`, `mapping/occupancy_grid.py`,
  `planning/astar.py`, `safety/safety_monitor.py`,
  `communication/state_manager.py`, the entire frontend.
- The WebSocket/REST API contract — the dashboard doesn't know or care
  whether `MotorController` is simulated or real.

## What changes

### 1. Camera source

Set `UGV_CAMERA_SOURCE` to whatever the onboard camera actually is.
`WebcamSource` already works unmodified if the onboard computer exposes the
camera as a standard V4L2 device (`/dev/videoN`) — just point
`UGV_CAMERA_DEVICE_INDEX` at it. For anything else, implement
`RTSPSource`/`IPStreamSource` for real (`backend/perception/camera.py`)
against your actual camera's stream URL and flip their `status` from
`NOT_IMPLEMENTED` to `ACTIVE` once verified — don't flip the label without
testing against the real stream.

### 2. Runtime mode + motor controller

Set `UGV_RUNTIME_MODE=HARDWARE`. This makes
`control.create_motor_controller` return `HardwareMotorController`, which
currently raises `NotImplementedError` on every call — that's intentional,
so nobody discovers "nothing is actually wired up" by watching a UGV not
move. Implement `HardwareMotorController.send()` and `.emergency_stop()`
(`backend/control/motor_controller.py`) against your actual motor
driver/serial link/CAN bus/ROS 2 topic. The interface it must satisfy is
just `VelocityCommand(linear_velocity: float, angular_velocity: float, command: MotionCommand)`
— everything upstream only ever produces that, never anything driver-
specific.

### 3. Collision checking without a simulator

`NavigationSystem._navigate_step` currently calls `self.simulator.tick(grid)`
for both motion integration *and* collision detection. On real hardware you
have neither — the UGV's actual position comes from
`LocalizationBackend.update()` (already real, ORB VO or a future SLAM
backend) and "collision" needs a different signal than a kinematic
simulation, e.g. a bump sensor, current-spike detection on the motor
driver, or simply trusting the traversability/planner pipeline more once
it's been field-validated. This is the one piece of `state_manager.py` that
needs a genuine HARDWARE-mode branch, not just a new backend — it isn't
written yet.

### 4. Camera/IMU calibration

`OrbVisualOdometry._ensure_camera_matrix` approximates the intrinsic matrix
from image width — fine for a rough webcam demo, not for a real UGV.
Calibrate the actual onboard camera (`cv2.calibrateCamera` with a
checkerboard) and load the real intrinsics instead. If the UGV has an IMU,
fusing it with the visual odometry (even a simple complementary filter on
heading) would meaningfully improve on the current "camera-only, no scale
ground-truth" limitation documented in `docs/architecture.md`.

### 5. Compute

`UGV_YOLO_DEVICE=auto` already picks CUDA if `torch.cuda.is_available()`.
On a Jetson, install the Jetson-specific PyTorch/torchvision build (NVIDIA
publishes these separately from PyPI) rather than the generic `pip install
torch` in `requirements.txt`. Drop to `yolo26n.pt` (already the default) or
reduce `UGV_YOLO_INFERENCE_SIZE` if frame rate on-device is too low —
measure with the TELEMETRY panel's inference FPS/latency readouts before
guessing.

## Suggested bring-up order

1. Get `WebcamSource`/`RTSPSource` producing frames from the real onboard
   camera with `UGV_RUNTIME_MODE` still `DEVELOPMENT` (simulated motion) —
   validates perception/traversability/localization against real hardware
   optics without any risk of the UGV actually moving.
2. Bench-test `HardwareMotorController` with the UGV on blocks — command
   FORWARD/TURN_LEFT/etc. by hand through the REST API and confirm wheels
   respond correctly before letting the planner drive them.
3. Switch to `UGV_RUNTIME_MODE=HARDWARE` and re-run the spec §25 test
   scenarios (clear path, single/multiple obstacles, blocked route, camera
   failure, communication failure) in a controlled space before an
   unsupervised demo.
