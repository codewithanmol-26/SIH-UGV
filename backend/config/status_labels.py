"""
Honesty labels (spec §30).

Every module that produces perception/localization/planning output must
tag it with one of these so the dashboard — and anyone reading logs — can
tell real algorithmic output from a placeholder.
"""
from enum import Enum


class ModuleStatus(str, Enum):
    ACTIVE = "ACTIVE"              # real algorithm, real output
    SIMULATED = "SIMULATED"        # synthetic data standing in for hardware/sensor
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"  # interface exists, no logic behind it yet


class NavigationState(str, Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    AUTONOMOUS = "AUTONOMOUS"
    PAUSED = "PAUSED"
    REROUTING = "REROUTING"
    SAFE_STOP = "SAFE_STOP"
    STOPPED = "STOPPED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    DESTINATION_REACHED = "DESTINATION_REACHED"
    CONNECTION_LOST = "CONNECTION_LOST"
    ERROR = "ERROR"


# Valid transitions: {from_state: {to_states...}}. EMERGENCY_STOP is reachable
# from every state (checked separately in the state machine, not listed here
# to avoid repeating it 12 times).
VALID_TRANSITIONS: dict[NavigationState, set[NavigationState]] = {
    NavigationState.IDLE: {NavigationState.INITIALIZING},
    NavigationState.INITIALIZING: {NavigationState.READY, NavigationState.ERROR},
    NavigationState.READY: {NavigationState.AUTONOMOUS, NavigationState.ERROR},
    NavigationState.AUTONOMOUS: {
        NavigationState.PAUSED,
        NavigationState.REROUTING,
        NavigationState.SAFE_STOP,
        NavigationState.DESTINATION_REACHED,
        NavigationState.STOPPED,
        NavigationState.CONNECTION_LOST,
        NavigationState.ERROR,
    },
    NavigationState.REROUTING: {
        NavigationState.AUTONOMOUS,
        NavigationState.SAFE_STOP,
        NavigationState.STOPPED,
    },
    NavigationState.PAUSED: {NavigationState.AUTONOMOUS, NavigationState.STOPPED},
    NavigationState.SAFE_STOP: {
        NavigationState.AUTONOMOUS,
        NavigationState.REROUTING,
        NavigationState.STOPPED,
    },
    NavigationState.CONNECTION_LOST: {NavigationState.AUTONOMOUS, NavigationState.STOPPED},
    NavigationState.DESTINATION_REACHED: {NavigationState.READY, NavigationState.IDLE},
    NavigationState.STOPPED: {NavigationState.READY, NavigationState.IDLE},
    NavigationState.ERROR: {NavigationState.IDLE},
    NavigationState.EMERGENCY_STOP: {NavigationState.STOPPED},
}
