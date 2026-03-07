"""
Machine state definitions and transition logic for the conveyor sorting cell.
Mirrors a PLC's internal state register.
"""

from enum import IntEnum


class MachineState(IntEnum):
    IDLE = 0
    AUTO_RUN = 1
    MANUAL = 2
    FAULT = 3
    ESTOP = 4


class FaultCode(IntEnum):
    NONE = 0
    JAM = 1               # Conveyor jam — jam sensor active > timer preset
    MOTOR_FEEDBACK = 2    # Motor feedback loss — run cmd ON, feedback OFF > 2s
    WATCHDOG = 3          # Watchdog / comms loss
    SENSOR_MISMATCH = 4   # Both size sensors active simultaneously


FAULT_DESCRIPTIONS = {
    FaultCode.NONE: "No fault",
    FaultCode.JAM: "Conveyor jam detected",
    FaultCode.MOTOR_FEEDBACK: "Motor run feedback lost",
    FaultCode.WATCHDOG: "Watchdog / communications loss",
    FaultCode.SENSOR_MISMATCH: "Size sensor mismatch (both active)",
}

ALARM_PRIORITIES = {
    FaultCode.JAM: "HIGH",
    FaultCode.MOTOR_FEEDBACK: "HIGH",
    FaultCode.WATCHDOG: "MEDIUM",
    FaultCode.SENSOR_MISMATCH: "MEDIUM",
}


class StateMachine:
    """
    Implements conveyor cell state transitions.
    Called once per scan cycle from ladder_routines.py.
    """

    def __init__(self):
        self.state = MachineState.IDLE
        self.fault_code = FaultCode.NONE
        self.last_fault_code = FaultCode.NONE
        # One-shot tracking for FAULT_RESET edge detection
        self._prev_fault_reset = False
        self._prev_estop = True  # NC contact: normally True (closed)

    def transition(self, tags: dict) -> None:
        """
        Evaluate all state transition conditions and update self.state.
        tags: current snapshot of the tag database (read-only usage here).
        """
        in_estop = tags["IN_ESTOP"]
        in_start = tags["IN_START_PB"]
        in_stop = tags["IN_STOP_PB"]
        in_mode = tags["IN_MODE_SELECT"]
        in_reset = tags["IN_FAULT_RESET"]
        fault_code = tags["HR_FAULT_CODE"]

        # Detect rising edge of FAULT_RESET (one-shot)
        reset_edge = in_reset and not self._prev_fault_reset
        self._prev_fault_reset = in_reset

        # Detect falling edge of E-STOP (NC contact opens = emergency)
        estop_fell = self._prev_estop and not in_estop
        self._prev_estop = in_estop

        # --- E-STOP overrides everything ---
        if estop_fell or (not in_estop and self.state not in (MachineState.ESTOP, MachineState.IDLE)):
            self.state = MachineState.ESTOP
            return

        # --- FAULT overrides AUTO/MANUAL ---
        if fault_code != FaultCode.NONE and self.state in (MachineState.AUTO_RUN, MachineState.MANUAL):
            self.state = MachineState.FAULT
            self.fault_code = FaultCode(fault_code)
            self.last_fault_code = self.fault_code
            return

        # State-specific transitions
        if self.state == MachineState.IDLE:
            if in_mode == 1:
                self.state = MachineState.MANUAL
            elif in_start and in_estop and fault_code == FaultCode.NONE:
                self.state = MachineState.AUTO_RUN

        elif self.state == MachineState.AUTO_RUN:
            if in_stop:
                self.state = MachineState.IDLE

        elif self.state == MachineState.MANUAL:
            if not in_estop:
                self.state = MachineState.ESTOP
            elif in_stop or in_mode == 0:
                self.state = MachineState.IDLE

        elif self.state == MachineState.FAULT:
            if reset_edge and fault_code == FaultCode.NONE:
                self.state = MachineState.IDLE
                self.fault_code = FaultCode.NONE

        elif self.state == MachineState.ESTOP:
            if in_estop and reset_edge:
                self.state = MachineState.IDLE
                self.fault_code = FaultCode.NONE
