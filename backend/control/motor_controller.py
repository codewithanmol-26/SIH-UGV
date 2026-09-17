"""
Motion control (spec §15). Hardware-independent: everything upstream talks
in linear/angular velocity or high-level commands, never in motor-driver
specifics, so plugging in a real UGV motor driver later means implementing
HardwareMotorController.send(...) and nothing else.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum

from config.status_labels import ModuleStatus


class MotionCommand(str, Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    STOP = "STOP"


@dataclass
class VelocityCommand:
    linear_velocity: float   # m/s, +forward
    angular_velocity: float  # rad/s, +counter-clockwise
    command: MotionCommand


class MotorController(abc.ABC):
    status: ModuleStatus = ModuleStatus.NOT_IMPLEMENTED

    @abc.abstractmethod
    def send(self, velocity: VelocityCommand) -> None:
        ...

    @abc.abstractmethod
    def emergency_stop(self) -> None:
        ...


class SimulationMotorController(MotorController):
    """Feeds velocity commands into simulation.simulator.UGVSimulator instead
    of a real motor driver. ACTIVE — this is genuinely how the MVP moves the
    simulated UGV, not a placeholder that's ignored."""

    status = ModuleStatus.SIMULATED

    def __init__(self, simulator) -> None:
        self._simulator = simulator
        self._last_command: VelocityCommand | None = None

    def send(self, velocity: VelocityCommand) -> None:
        self._last_command = velocity
        self._simulator.apply_velocity(velocity.linear_velocity, velocity.angular_velocity)

    def emergency_stop(self) -> None:
        self.send(VelocityCommand(0.0, 0.0, MotionCommand.STOP))

    @property
    def last_command(self) -> VelocityCommand | None:
        return self._last_command


class HardwareMotorController(MotorController):
    """Reserved for a real motor driver (serial, CAN, ROS 2 topic, etc.) on
    the onboard UGV computer. NOT_IMPLEMENTED — deliberately raises instead
    of silently doing nothing, so nobody discovers the hard way that a
    physical UGV isn't actually receiving commands."""

    status = ModuleStatus.NOT_IMPLEMENTED

    def send(self, velocity: VelocityCommand) -> None:
        raise NotImplementedError(
            "HardwareMotorController has no driver wired up yet. "
            "Implement send() for your motor driver/serial/CAN/ROS2 interface "
            "before setting UGV_RUNTIME_MODE=HARDWARE."
        )

    def emergency_stop(self) -> None:
        raise NotImplementedError("HardwareMotorController.emergency_stop() not implemented.")


def create_motor_controller(runtime_mode: str, simulator) -> MotorController:
    if runtime_mode == "DEVELOPMENT":
        return SimulationMotorController(simulator)
    if runtime_mode == "HARDWARE":
        return HardwareMotorController()
    raise ValueError(f"Unknown runtime mode: {runtime_mode}")
