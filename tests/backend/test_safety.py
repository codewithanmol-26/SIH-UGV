from config.status_labels import NavigationState
from safety.safety_monitor import SafetyMonitor, SafetyVerdict


def _monitor():
    return SafetyMonitor(camera_timeout_s=2.0, low_confidence_threshold=0.35)


def test_camera_lost_triggers_safe_stop():
    v = _monitor().check(
        system_initialized=True, camera_is_stale=True, localization_confidence=0.9,
        planner_found_path=True, emergency_stop_requested=False,
        current_state=NavigationState.AUTONOMOUS,
    )
    assert v.verdict == SafetyVerdict.SAFE_STOP


def test_low_localization_confidence_triggers_safe_stop():
    v = _monitor().check(
        system_initialized=True, camera_is_stale=False, localization_confidence=0.1,
        planner_found_path=True, emergency_stop_requested=False,
        current_state=NavigationState.AUTONOMOUS,
    )
    assert v.verdict == SafetyVerdict.SAFE_STOP


def test_no_valid_path_triggers_safe_stop():
    v = _monitor().check(
        system_initialized=True, camera_is_stale=False, localization_confidence=0.9,
        planner_found_path=False, emergency_stop_requested=False,
        current_state=NavigationState.AUTONOMOUS,
    )
    assert v.verdict == SafetyVerdict.SAFE_STOP


def test_emergency_stop_overrides_everything():
    v = _monitor().check(
        system_initialized=True, camera_is_stale=False, localization_confidence=0.9,
        planner_found_path=True, emergency_stop_requested=True,
        current_state=NavigationState.AUTONOMOUS,
    )
    assert v.verdict == SafetyVerdict.BLOCK_MOVEMENT


def test_uninitialized_system_blocks_movement():
    v = _monitor().check(
        system_initialized=False, camera_is_stale=False, localization_confidence=0.9,
        planner_found_path=True, emergency_stop_requested=False,
        current_state=NavigationState.IDLE,
    )
    assert v.verdict == SafetyVerdict.BLOCK_MOVEMENT


def test_nominal_conditions_are_ok():
    v = _monitor().check(
        system_initialized=True, camera_is_stale=False, localization_confidence=0.9,
        planner_found_path=True, emergency_stop_requested=False,
        current_state=NavigationState.AUTONOMOUS,
    )
    assert v.verdict == SafetyVerdict.OK


def test_low_confidence_in_non_autonomous_state_is_not_flagged():
    # A READY (not-yet-moving) UGV shouldn't SAFE_STOP over localization
    # confidence it hasn't had a chance to build yet.
    v = _monitor().check(
        system_initialized=True, camera_is_stale=False, localization_confidence=0.0,
        planner_found_path=True, emergency_stop_requested=False,
        current_state=NavigationState.READY,
    )
    assert v.verdict == SafetyVerdict.OK
