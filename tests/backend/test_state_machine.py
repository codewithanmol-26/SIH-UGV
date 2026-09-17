from config.status_labels import NavigationState
from communication.state_manager import NavigationStateMachine


def test_initial_state_is_idle():
    fsm = NavigationStateMachine()
    assert fsm.state == NavigationState.IDLE


def test_happy_path_transitions():
    fsm = NavigationStateMachine()
    assert fsm.transition(NavigationState.INITIALIZING)
    assert fsm.transition(NavigationState.READY)
    assert fsm.transition(NavigationState.AUTONOMOUS)
    assert fsm.transition(NavigationState.DESTINATION_REACHED)
    assert fsm.transition(NavigationState.IDLE)


def test_invalid_transition_rejected():
    fsm = NavigationStateMachine()
    # Can't jump straight from IDLE to AUTONOMOUS.
    assert not fsm.transition(NavigationState.AUTONOMOUS)
    assert fsm.state == NavigationState.IDLE


def test_emergency_stop_overrides_from_any_state():
    for start_state in NavigationState:
        fsm = NavigationStateMachine()
        fsm.state = start_state
        assert fsm.transition(NavigationState.EMERGENCY_STOP), f"e-stop should override from {start_state}"


def test_rerouting_can_recover_to_autonomous():
    fsm = NavigationStateMachine()
    fsm.state = NavigationState.REROUTING
    assert fsm.transition(NavigationState.AUTONOMOUS)


def test_safe_stop_can_lead_to_stopped():
    fsm = NavigationStateMachine()
    fsm.state = NavigationState.SAFE_STOP
    assert fsm.transition(NavigationState.STOPPED)
