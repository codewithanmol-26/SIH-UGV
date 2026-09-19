"""
Traversable-area detection (spec §9).

Object detection alone doesn't tell the planner where it's *safe to drive*
between/around the detected obstacles — that's this module's job: produce a
per-pixel TRAVERSABLE / OBSTACLE / UNKNOWN mask for the current frame.

Two interchangeable strategies behind one interface (TraversabilityEstimator):

  ClassicalTraversabilityEstimator (ACTIVE)
      Geometric/color-texture ground-plane heuristic:
        1. Sample a trapezoid at the bottom-center of the frame, assumed to
           be drivable ground directly in front of the UGV (a reasonable
           prior for an outdoor path/trail).
        2. Build a color histogram model of that "ground" sample in HSV.
        3. Classify every pixel in the frame by similarity to that model
           (back-projection) -> smooth with morphological ops -> mask.
        4. Cut out any region covered by a YOLO obstacle box (those are
           OBSTACLE regardless of color similarity).
      This is a real, working algorithm — not a stub — but it's a
      brightness/texture heuristic, not learned segmentation, so it will
      misclassify shadowed grass, wet rock, etc. That's expected of a
      classical-CV first pass.

  SegmentationTraversabilityEstimator (NOT_IMPLEMENTED)
      Interface reserved for a YOLO26-seg (or other) learned segmentation
      model. Swapping settings.traversability_method to "segmentation" once
      this class has a real forward pass is the only change needed — the
      planner only ever consumes a TraversabilityResult.mask, never knows
      which estimator produced it.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

import cv2
import numpy as np

from config.status_labels import ModuleStatus
from perception.detector import Detection

TRAVERSABLE = 0
OBSTACLE = 1
UNKNOWN = 2


@dataclass
class TraversabilityResult:
    # uint8 mask, same H x W as the input frame, values in {TRAVERSABLE, OBSTACLE, UNKNOWN}
    mask: np.ndarray
    drivable_confidence: float  # fraction of the near-field trapezoid classified TRAVERSABLE
    status: ModuleStatus


class TraversabilityEstimator(abc.ABC):
    status: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED

    @abc.abstractmethod
    def estimate(self, frame_bgr: np.ndarray, detections: list[Detection]) -> TraversabilityResult:
        ...


class ClassicalTraversabilityEstimator(TraversabilityEstimator):
    status = ModuleStatus.ACTIVE

    def __init__(self, sample_fraction: float = 0.18) -> None:
        # Fraction of the frame height used as the "known ground" sample
        # region at the bottom-center of the image.
        self._sample_fraction = sample_fraction

    def _ground_sample_mask(self, h: int, w: int) -> np.ndarray:
        mask = np.zeros((h, w), dtype=np.uint8)
        sample_h = int(h * self._sample_fraction)
        # Trapezoid narrower at the top, matching typical forward-path perspective.
        top_y = h - sample_h
        pts = np.array([
            [int(w * 0.35), top_y],
            [int(w * 0.65), top_y],
            [int(w * 0.85), h - 1],
            [int(w * 0.15), h - 1],
        ], dtype=np.int32)
        cv2.fillConvexPoly(mask, pts, 255)
        return mask

    def estimate(self, frame_bgr: np.ndarray, detections: list[Detection]) -> TraversabilityResult:
        h, w = frame_bgr.shape[:2]
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

        sample_mask = self._ground_sample_mask(h, w)
        hist = cv2.calcHist([hsv], [0, 1], sample_mask, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 255, cv2.NORM_MINMAX)

        back_proj = cv2.calcBackProject([hsv], [0, 1], hist, [0, 180, 0, 256], 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cv2.filter2D(back_proj, -1, kernel, back_proj)
        _, similarity_mask = cv2.threshold(back_proj, 50, 255, cv2.THRESH_BINARY)
        similarity_mask = cv2.morphologyEx(similarity_mask, cv2.MORPH_OPEN, kernel)
        similarity_mask = cv2.morphologyEx(similarity_mask, cv2.MORPH_CLOSE, kernel)

        mask = np.full((h, w), UNKNOWN, dtype=np.uint8)
        mask[similarity_mask > 0] = TRAVERSABLE
        # Anything that looked like open ground *and* is below the horizon
        # line we already sampled from counts as traversable; everything
        # else defaults to UNKNOWN rather than assuming it's safe.
        mask[:int(h * 0.3), :] = UNKNOWN  # sky/horizon band is never "ground"

        # Detected obstacles always override the color heuristic.
        for det in detections:
            x1, y1 = max(0, int(det.x)), max(0, int(det.y))
            x2, y2 = min(w, int(det.x + det.w)), min(h, int(det.y + det.h))
            mask[y1:y2, x1:x2] = OBSTACLE

        near_field = mask[int(h * (1 - self._sample_fraction)):, :]
        drivable_confidence = float(np.mean(near_field == TRAVERSABLE)) if near_field.size else 0.0

        return TraversabilityResult(
            mask=mask,
            drivable_confidence=round(drivable_confidence, 3),
            status=ModuleStatus.ACTIVE,
        )


class SegmentationTraversabilityEstimator(TraversabilityEstimator):
    """Reserved for a YOLO26-seg (ultralytics/cfg/models/26/yolo26-seg.yaml)
    or other learned segmentation model. Not implemented — calling estimate()
    raises rather than silently returning fake data."""

    status = ModuleStatus.NOT_IMPLEMENTED

    def estimate(self, frame_bgr: np.ndarray, detections: list[Detection]) -> TraversabilityResult:
        raise NotImplementedError(
            "SegmentationTraversabilityEstimator is not implemented yet. "
            "Set UGV_TRAVERSABILITY_METHOD=classical, or implement this class "
            "against yolo26-seg / another segmentation model."
        )


def create_traversability_estimator(method: str) -> TraversabilityEstimator:
    if method == "classical":
        return ClassicalTraversabilityEstimator()
    if method == "segmentation":
        return SegmentationTraversabilityEstimator()
    raise ValueError(f"Unknown traversability method: {method}")
