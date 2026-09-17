"""
Visual localization (spec §10). GPS-denied by design — this is the only
source of UGV position/heading in the system.

Status: ACTIVE for a monocular ORB feature-matching visual-odometry
prototype. This is explicitly a prototype, not SLAM: it estimates relative
motion frame-to-frame (rotation + *direction* of translation) via the
essential matrix, but monocular VO cannot recover absolute translation
scale from geometry alone. We assume a constant forward speed-to-pixel-flow
scale calibrated for typical walking-pace UGV motion (see _ASSUMED_SCALE_M)
— this is a known, documented limitation, not something the dashboard
should present as survey-grade positioning. drift accumulates over time
with no loop closure, exactly like any un-corrected VO/dead-reckoning
system.

LocalizationInterface is written so a future ORB-SLAM3, visual-inertial, or
stereo-depth backend can be dropped in without touching mapping/planning —
both must only produce a Pose (x, y, heading, confidence).
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass

import cv2
import numpy as np

from config.status_labels import ModuleStatus


@dataclass
class Pose:
    x: float
    y: float
    heading_deg: float
    confidence: float  # 0..1, from feature-match quality
    timestamp: float
    status: ModuleStatus


class LocalizationBackend(abc.ABC):
    status: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED

    @abc.abstractmethod
    def update(self, frame_bgr: np.ndarray) -> Pose:
        ...

    @abc.abstractmethod
    def reset(self, x: float = 0.0, y: float = 0.0, heading_deg: float = 0.0) -> None:
        ...


# Assumed forward distance (meters) a "typical" frame-to-frame ORB
# translation vector represents at ~30fps and walking-pace UGV speed.
# This is a calibration placeholder — replace with a real scale estimate
# (wheel odometry fusion, IMU integration, or stereo depth) before trusting
# absolute distances from this module.
_ASSUMED_SCALE_M = 0.05


class OrbVisualOdometry(LocalizationBackend):
    status = ModuleStatus.ACTIVE

    def __init__(self, min_matches: int = 25, low_confidence_threshold: float = 0.35) -> None:
        self._orb = cv2.ORB_create(nfeatures=1000)
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self._min_matches = min_matches
        self._low_confidence_threshold = low_confidence_threshold

        self._prev_gray: np.ndarray | None = None
        self._prev_kp = None
        self._prev_des = None
        self._camera_matrix: np.ndarray | None = None

        self._x = 0.0
        self._y = 0.0
        self._heading_deg = 0.0

    def reset(self, x: float = 0.0, y: float = 0.0, heading_deg: float = 0.0) -> None:
        self._x, self._y, self._heading_deg = x, y, heading_deg
        self._prev_gray = self._prev_kp = self._prev_des = None

    def _ensure_camera_matrix(self, w: int, h: int) -> np.ndarray:
        if self._camera_matrix is None:
            # No calibration file available yet — approximate focal length
            # from image width, a common rough default for consumer webcams.
            focal = w
            self._camera_matrix = np.array([
                [focal, 0, w / 2],
                [0, focal, h / 2],
                [0, 0, 1],
            ], dtype=np.float64)
        return self._camera_matrix

    def update(self, frame_bgr: np.ndarray) -> Pose:
        now = time.time()
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        K = self._ensure_camera_matrix(w, h)

        kp, des = self._orb.detectAndCompute(gray, None)

        if self._prev_des is None or des is None or len(kp) < 8:
            self._prev_gray, self._prev_kp, self._prev_des = gray, kp, des
            return Pose(self._x, self._y, self._heading_deg, confidence=0.0,
                        timestamp=now, status=ModuleStatus.ACTIVE)

        matches = self._matcher.match(self._prev_des, des)
        matches = sorted(matches, key=lambda m: m.distance)

        confidence = min(1.0, len(matches) / (self._min_matches * 3))

        if len(matches) >= self._min_matches:
            pts_prev = np.float32([self._prev_kp[m.queryIdx].pt for m in matches])
            pts_curr = np.float32([kp[m.trainIdx].pt for m in matches])

            E, mask = cv2.findEssentialMat(pts_curr, pts_prev, K, method=cv2.RANSAC,
                                            prob=0.999, threshold=1.0)
            if E is not None and E.shape == (3, 3):
                _, R, t, _ = cv2.recoverPose(E, pts_curr, pts_prev, K, mask=mask)

                # Yaw from the rotation matrix (image x/z plane -> ground plane).
                dyaw_rad = float(np.arctan2(R[0, 2], R[2, 2]))
                dyaw_deg = np.degrees(dyaw_rad)

                heading_rad = np.radians(self._heading_deg)
                dx_local = float(t[2, 0]) * _ASSUMED_SCALE_M  # forward component
                dz_local = float(t[0, 0]) * _ASSUMED_SCALE_M  # lateral component

                self._x += dx_local * np.cos(heading_rad) - dz_local * np.sin(heading_rad)
                self._y += dx_local * np.sin(heading_rad) + dz_local * np.cos(heading_rad)
                self._heading_deg = (self._heading_deg + dyaw_deg) % 360.0
            else:
                confidence *= 0.3  # essential matrix failed — trust this update less

        self._prev_gray, self._prev_kp, self._prev_des = gray, kp, des

        return Pose(
            x=round(self._x, 3),
            y=round(self._y, 3),
            heading_deg=round(self._heading_deg, 1),
            confidence=round(confidence, 3),
            timestamp=now,
            status=ModuleStatus.ACTIVE,
        )


class Slam3Backend(LocalizationBackend):
    """Reserved integration point for ORB-SLAM3 / visual-inertial odometry /
    stereo-depth localization. Not implemented — raises rather than
    pretending to localize."""

    status = ModuleStatus.NOT_IMPLEMENTED

    def update(self, frame_bgr: np.ndarray) -> Pose:
        raise NotImplementedError("SLAM3 backend is not implemented. Use orb_vo.")

    def reset(self, x: float = 0.0, y: float = 0.0, heading_deg: float = 0.0) -> None:
        raise NotImplementedError("SLAM3 backend is not implemented. Use orb_vo.")


def create_localization_backend(method: str, min_matches: int, low_confidence_threshold: float) -> LocalizationBackend:
    if method == "orb_vo":
        return OrbVisualOdometry(min_matches, low_confidence_threshold)
    if method == "slam3":
        return Slam3Backend()
    raise ValueError(f"Unknown localization method: {method}")
