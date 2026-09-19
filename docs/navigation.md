# Navigation

## State machine

```
IDLE → INITIALIZING → READY → AUTONOMOUS ⇄ PAUSED
                         │         │  │
                         │         │  ├→ REROUTING → AUTONOMOUS
                         │         │  │           └→ SAFE_STOP / STOPPED
                         │         │  ├→ SAFE_STOP → AUTONOMOUS / REROUTING / STOPPED
                         │         │  ├→ DESTINATION_REACHED → READY / IDLE
                         │         │  └→ CONNECTION_LOST → AUTONOMOUS / STOPPED
                         │         └→ STOPPED → READY / IDLE
                         └→ ERROR → IDLE

EMERGENCY_STOP is reachable from *every* state and leads only to STOPPED.
```

Defined as data in `backend/config/status_labels.py::VALID_TRANSITIONS`
rather than an if/elif chain, and enforced by
`NavigationStateMachine.transition()`
(`backend/communication/state_manager.py`) — a transition not in that table
is simply rejected (`transition()` returns `False`; the REST layer turns
that into a `409`).

`EMERGENCY_STOP` is checked separately, before the table lookup, precisely
so it always wins regardless of current state — the one deliberate
exception to "only listed transitions are valid."

## Why emergency-stop recovery requires a restart

`clear_emergency_stop()` exists in `NavigationSystem` and moves
`EMERGENCY_STOP → STOPPED`, but there's no path from there back to
`AUTONOMOUS` without going through `READY`, which requires
`NavigationSystem.initialize()` to run again. That's deliberate for an MVP:
"the UGV silently resumes after an e-stop" is exactly the failure mode a
physical safety review would flag first. Re-initializing forces a fresh
camera/model/localization bring-up before autonomy is allowed again.

## Dynamic obstacle avoidance

Every tick while `AUTONOMOUS`/`REROUTING` (`NavigationSystem._navigate_step`):

1. Check whether any waypoint in the **current** plan now sits on an
   `OCC_OBSTACLE` cell (`_plan_is_blocked`). If so, transition to
   `REROUTING` and force a replan this tick.
2. Otherwise, replan on a fixed interval anyway
   (`UGV_PLANNER_REPLAN_INTERVAL_S`, default 1s) — obstacles the UGV has
   just seen for the first time may not yet intersect the *existing* plan
   but should still influence the *next* one.
3. If A* finds a path: if we were `REROUTING`, go back to `AUTONOMOUS` and
   log it. If not: `SAFE_STOP` and log "No safe path found."
4. Compute a `VelocityCommand` toward the next waypoint (proportional
   heading control — turn rate scales with heading error, forward speed
   backs off for sharp turns) and send it to the motor controller.
5. Tick the simulator against the *current* grid. If the simulator's
   footprint overlaps an obstacle cell despite all of the above, that's
   treated as a genuine collision → `SAFE_STOP`, not just a planning
   near-miss.

This is exactly the sequence in spec §13/§29: detect → update map → check
blocked → replan → continue, without stopping unnecessarily when a valid
alternative exists (`UNKNOWN` cells cost more than `FREE` but are never a
hard block, so the UGV doesn't freeze the moment it hasn't seen a patch of
ground yet).

## Safety rules (spec §19)

Implemented as pure vetoes in `backend/safety/safety_monitor.py`, called
before any movement decision each tick:

| Condition | Verdict |
|---|---|
| Emergency stop requested | `BLOCK_MOVEMENT` |
| System not initialized (perception never loaded) | `BLOCK_MOVEMENT` |
| Camera feed stale (`UGV_CAMERA_TIMEOUT_S`, default 2s) | `SAFE_STOP` |
| Localization confidence below threshold, while `AUTONOMOUS`/`REROUTING` | `SAFE_STOP` (or `SLOW_MODE`, configurable) |
| No path found | `SAFE_STOP` |
| Otherwise | `OK` |

A `SafetyVerdict` always overrides whatever the planner/controller wanted to
do that tick — `state_manager._run_safety_and_control` checks it first and
returns early on anything other than `OK`.

## Known limitations of the planner/localization combination

The planner trusts whatever the occupancy grid says, and the grid is built
from the traversability mask projected using the *current estimated pose*.
If localization confidence is low, the grid (and therefore the plan) is
built on a shaky position estimate — which is exactly why low confidence
triggers `SAFE_STOP` rather than letting the planner charge ahead on bad
data.
