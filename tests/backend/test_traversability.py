import numpy as np

from perception.traversability import (
    ClassicalTraversabilityEstimator, SegmentationTraversabilityEstimator,
    TRAVERSABLE, OBSTACLE,
)
from perception.detector import Detection


def _synthetic_ground_frame(w=320, h=240):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :] = (40, 90, 40)     # ground
    frame[: int(h * 0.3), :] = (180, 140, 90)  # sky band
    return frame


def test_classical_estimator_marks_obstacle_box():
    frame = _synthetic_ground_frame()
    det = Detection(cls_name="rock", confidence=0.9, x=100, y=150, w=40, h=40, timestamp=0.0)
    result = ClassicalTraversabilityEstimator().estimate(frame, [det])
    assert result.mask[170, 120] == OBSTACLE


def test_classical_estimator_sky_band_is_never_traversable():
    frame = _synthetic_ground_frame(h=240)
    result = ClassicalTraversabilityEstimator().estimate(frame, [])
    from perception.traversability import UNKNOWN
    assert np.all(result.mask[:50, :] != TRAVERSABLE)
    assert np.any(result.mask[:50, :] == UNKNOWN)


def test_classical_estimator_drivable_confidence_in_range():
    frame = _synthetic_ground_frame()
    result = ClassicalTraversabilityEstimator().estimate(frame, [])
    assert 0.0 <= result.drivable_confidence <= 1.0


def test_segmentation_estimator_raises_not_implemented():
    frame = _synthetic_ground_frame()
    try:
        SegmentationTraversabilityEstimator().estimate(frame, [])
        assert False, "expected NotImplementedError"
    except NotImplementedError:
        pass
