"""
Safety rules (spec §19). This module doesn't make navigation decisions — it
only ever *vetoes* them. communication/state_manager.py asks
SafetyMonitor.check(...) before every AUTONOMOUS-state tick and applies the
resulting verdict; safety-triggered transitions always win over whatever
the planner wanted to do.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from config.status_labels import ModuleStatus, NavigationState


class SafetyVerdict(str, Enum):
    OK = "OK"
    SAFE_STOP = "SAFE_STOP"
    SLOW_MODE = "SLOW_MODE"
    BLOCK_MOVEMENT = "BLOCK_MOVEMENT"


@dataclass
class SafetyCheckResult:
    verdict: SafetyVerdict
    reason: str


class SafetyMonitor:
    status = ModuleStatus.ACTIVE

    def __init__(self, camera_timeout_s: float, low_confidence_threshold: float,
                 low_confidence_mode: str = "SAFE_STOP") -> None:
        self._camera_timeout_s = camera_timeout_s
        self._low_confidence_threshold = low_confidence_threshold
        self._low_confidence_mode = low_confidence_mode  # "SAFE_STOP" or "SLOW_MODE"

    def check(
        self,
        *,
        system_initialized: bool,
        camera_is_stale: bool,
        localization_confidence: float,
        planner_found_path: bool,
        emergency_stop_requested: bool,
        current_state: NavigationState,
    ) -> SafetyCheckResult:
        if emergency_stop_requested:
            return SafetyCheckResult(SafetyVerdict.BLOCK_MOVEMENT, "Emergency stop requested")

        if not system_initialized:
            return SafetyCheckResult(SafetyVerdict.BLOCK_MOVEMENT, "System not initialized")

        if camera_is_stale:
            return SafetyCheckResult(SafetyVerdict.SAFE_STOP, "Camera feed lost/stale")

        if current_state in (NavigationState.AUTONOMOUS, NavigationState.REROUTING):
            if localization_confidence < self._low_confidence_threshold:
                if self._low_confidence_mode == "SLOW_MODE":
                    return SafetyCheckResult(SafetyVerdict.SLOW_MODE, "Low localization confidence")
                return SafetyCheckResult(SafetyVerdict.SAFE_STOP, "Low localization confidence")

            if not planner_found_path:
                return SafetyCheckResult(SafetyVerdict.SAFE_STOP, "No valid path to destination")

        return SafetyCheckResult(SafetyVerdict.OK, "Nominal")
