"""
Unified camera abstraction (spec §6).

CameraSource is the interface the rest of the pipeline (detector,
traversability, visual odometry) depends on. Swapping the physical camera
never touches those modules — only which CameraSource subclass main.py
instantiates.

Status:
    WebcamSource     -> ACTIVE   (real cv2.VideoCapture against a laptop webcam)
    VideoFileSource   -> ACTIVE   (real cv2.VideoCapture against a video file, looped)
    IPStreamSource    -> NOT_IMPLEMENTED (interface only; MJPEG/HTTP stream from a phone)
    RTSPSource        -> NOT_IMPLEMENTED (interface only; same VideoCapture backend, RTSP URL)
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass

import cv2
import numpy as np

from config.status_labels import ModuleStatus


@dataclass
class Frame:
    image: np.ndarray          # BGR, HxWx3 uint8
    timestamp: float           # time.monotonic() when captured
    frame_index: int
    width: int
    height: int


class CameraSource(abc.ABC):
    status: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED

    def __init__(self) -> None:
        self._frame_index = 0
        self._last_frame_time: float | None = None

    @abc.abstractmethod
    def open(self) -> bool:
        """Open the underlying capture device/file. Returns True on success."""

    @abc.abstractmethod
    def read(self) -> Frame | None:
        """Return the next frame, or None if the source has no frame ready."""

    @abc.abstractmethod
    def release(self) -> None:
        ...

    def is_stale(self, timeout_s: float) -> bool:
        """True if no frame has arrived within timeout_s — feeds the safety monitor."""
        if self._last_frame_time is None:
            return False
        return (time.monotonic() - self._last_frame_time) > timeout_s

    @property
    def is_open(self) -> bool:
        raise NotImplementedError


class _OpenCVCaptureSource(CameraSource):
    """Shared implementation for anything cv2.VideoCapture can open
    (webcam index, video file path, or an RTSP/HTTP URL)."""

    status = ModuleStatus.ACTIVE

    def __init__(self, capture_target, loop_video: bool = False,
                 target_width: int | None = None, target_height: int | None = None) -> None:
        super().__init__()
        self._target = capture_target
        self._loop = loop_video
        self._target_width = target_width
        self._target_height = target_height
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self._target)
        if self._target_width:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._target_width)
        if self._target_height:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._target_height)
        return bool(self._cap.isOpened())

    def read(self) -> Frame | None:
        if self._cap is None or not self._cap.isOpened():
            return None
        ok, image = self._cap.read()
        if not ok or image is None:
            if self._loop:
                # Recorded video reached EOF — rewind so a demo run can loop.
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, image = self._cap.read()
                if not ok:
                    return None
            else:
                return None
        self._frame_index += 1
        self._last_frame_time = time.monotonic()
        h, w = image.shape[:2]
        return Frame(image=image, timestamp=self._last_frame_time,
                     frame_index=self._frame_index, width=w, height=h)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()


class WebcamSource(_OpenCVCaptureSource):
    """Laptop/onboard USB webcam, by device index. ACTIVE."""

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480) -> None:
        super().__init__(capture_target=device_index, loop_video=False,
                          target_width=width, target_height=height)


class VideoFileSource(_OpenCVCaptureSource):
    """Recorded outdoor video, looped so a demo can run indefinitely. ACTIVE."""

    def __init__(self, path: str) -> None:
        super().__init__(capture_target=path, loop_video=True)


class IPStreamSource(CameraSource):
    """Mobile-phone HTTP/MJPEG stream (e.g. the 'IP Webcam' Android app).

    NOT_IMPLEMENTED: cv2.VideoCapture can usually open an MJPEG HTTP URL
    directly (same code path as _OpenCVCaptureSource), but that needs
    testing against a real phone stream to pick sane timeouts/retry logic
    before it's honestly labelled ACTIVE. Wire it up by pointing
    _OpenCVCaptureSource at settings.camera_ip_url once verified.
    """

    status = ModuleStatus.NOT_IMPLEMENTED

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def open(self) -> bool:
        return False

    def read(self) -> Frame | None:
        return None

    def release(self) -> None:
        return None

    @property
    def is_open(self) -> bool:
        return False


class RTSPSource(CameraSource):
    """RTSP camera stream. NOT_IMPLEMENTED for the same reason as IPStreamSource
    — the plumbing is identical to _OpenCVCaptureSource, but needs a real RTSP
    source to validate reconnect behaviour before being called ACTIVE."""

    status = ModuleStatus.NOT_IMPLEMENTED

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def open(self) -> bool:
        return False

    def read(self) -> Frame | None:
        return None

    def release(self) -> None:
        return None

    @property
    def is_open(self) -> bool:
        return False


def create_camera_source(kind: str, settings) -> CameraSource:
    """Factory used by main.py so switching camera_source in settings/.env
    is the only change needed anywhere in the system."""
    if kind == "webcam":
        return WebcamSource(settings.camera_device_index, settings.camera_width, settings.camera_height)
    if kind == "video_file":
        return VideoFileSource(settings.camera_video_path)
    if kind == "ip_stream":
        return IPStreamSource(settings.camera_ip_url)
    if kind == "rtsp":
        return RTSPSource(settings.camera_rtsp_url)
    raise ValueError(f"Unknown camera source kind: {kind}")
