"""
Obstacle detection (spec §7, §8) using the latest stable Ultralytics YOLO26.

Status: ACTIVE. Runs real inference through ultralytics' YOLO class. Weights
(default: yolo26n.pt, the nano variant) are auto-downloaded by ultralytics
from the official release assets on first use if not already present under
models/.

The model is deliberately swappable: everything downstream only depends on
the plain-Python Detection objects this module returns, never on
ultralytics' Results object, so replacing YOLO26 with a future model means
editing this one file.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from config.settings import settings
from config.status_labels import ModuleStatus

# Outdoor-hazard classes we care about, mapped from COCO's default 80
# classes. COCO is not sufficient for real UGV hazards (rocks, ditches,
# loose terrain have no COCO class) — this list is a starting point, and
# perception/README-style note below documents where custom classes plug in.
COCO_HAZARD_CLASSES = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "dog", "horse", "sheep", "cow", "bench", "fire hydrant",
    "stop sign", "potted plant",
}


@dataclass
class Detection:
    cls_name: str
    confidence: float
    # Bounding box in image pixel coordinates (x, y = top-left corner).
    x: float
    y: float
    w: float
    h: float
    timestamp: float
    # Position within the frame, normalized 0..1, used by traversability/
    # planning without needing to know the frame resolution. This is NOT a
    # physical distance — see module docstring in localization/ for why.
    image_x_norm: float = 0.0
    image_y_norm: float = 0.0


@dataclass
class DetectionResult:
    detections: list[Detection] = field(default_factory=list)
    inference_ms: float = 0.0
    status: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED
    model_name: str = ""


class ObstacleDetector:
    status = ModuleStatus.ACTIVE

    def __init__(self) -> None:
        self._model = None
        self._device = self._resolve_device()

    def _resolve_device(self) -> str:
        if settings.yolo_device != "auto":
            return settings.yolo_device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def load(self) -> None:
        """Lazily import ultralytics (it's slow to import) and load weights.
        Ultralytics handles the actual download-if-missing itself."""
        from ultralytics import YOLO

        self._model = YOLO(settings.yolo_weights_path or settings.yolo_model_name)

    def infer(self, frame_bgr: np.ndarray) -> DetectionResult:
        if self._model is None:
            self.load()

        t0 = time.perf_counter()
        results = self._model.predict(
            source=frame_bgr,
            imgsz=settings.yolo_inference_size,
            conf=settings.yolo_confidence_threshold,
            iou=settings.yolo_iou_threshold,
            device=self._device,
            verbose=False,
        )
        inference_ms = (time.perf_counter() - t0) * 1000.0

        h, w = frame_bgr.shape[:2]
        detections: list[Detection] = []
        now = time.time()

        if results:
            r = results[0]
            names = r.names
            if r.boxes is not None:
                for box in r.boxes:
                    xyxy = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = names.get(cls_id, str(cls_id))
                    x1, y1, x2, y2 = xyxy
                    bw, bh = x2 - x1, y2 - y1
                    detections.append(Detection(
                        cls_name=cls_name,
                        confidence=round(conf, 3),
                        x=x1, y=y1, w=bw, h=bh,
                        timestamp=now,
                        image_x_norm=(x1 + bw / 2) / w,
                        image_y_norm=(y1 + bh) / h,  # bottom-center: where object meets ground
                    ))

        return DetectionResult(
            detections=detections,
            inference_ms=round(inference_ms, 2),
            status=ModuleStatus.ACTIVE,
            model_name=settings.yolo_model_name,
        )
