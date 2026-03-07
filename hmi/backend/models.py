"""Pydantic models for HMI API request/response."""

from pydantic import BaseModel
from typing import Optional


class CommandRequest(BaseModel):
    """Write a command to the PLC via Modbus HR[4]."""
    command: int  # 1=START 2=STOP 3=RESET 4=SHIFT_RESET


class WriteRequest(BaseModel):
    """Write a value to a named holding register."""
    tag: str
    value: int


class AlarmAckRequest(BaseModel):
    alarm_id: int


class AlarmRecord(BaseModel):
    id: int
    timestamp: str
    alarm_code: int
    description: str
    priority: str
    acknowledged: bool
    ack_timestamp: Optional[str] = None


class EventRecord(BaseModel):
    id: int
    timestamp: str
    event_type: str
    description: str
    value: Optional[str] = None


class ProductionSnapshot(BaseModel):
    timestamp: str
    shift_date: str
    box_total: int
    box_small: int
    box_large: int
    box_metal: int
    throughput_per_hr: float


class TagSnapshot(BaseModel):
    """All live tags pushed over WebSocket."""
    # Coil outputs
    OUT_MOTOR_RUN: bool
    OUT_GATE_A: bool
    OUT_GATE_B: bool
    OUT_GATE_C: bool
    OUT_ALARM_HORN: bool
    OUT_ESTOP_LIGHT: bool
    OUT_FAULT_LIGHT: bool
    OUT_RUN_LIGHT: bool
    OUT_HEARTBEAT: bool
    # Discrete inputs
    IN_ESTOP: bool
    IN_JAM_SENSOR: bool
    IN_BOX_DETECT: bool
    IN_SIZE_SMALL: bool
    IN_SIZE_LARGE: bool
    IN_METAL_DETECT: bool
    IN_MOTOR_FEEDBACK: bool
    IN_GATE_A_CONFIRM: bool
    IN_GATE_B_CONFIRM: bool
    # Holding registers
    HR_SPEED_SETPOINT: int
    HR_JAM_TIMER_PRESET: int
    HR_FAULT_CODE: int
    HR_MODE_COMMAND: int
    # Input registers
    IR_BOX_COUNT_TOTAL: int
    IR_BOX_COUNT_SMALL: int
    IR_BOX_COUNT_LARGE: int
    IR_BOX_COUNT_METAL: int
    IR_SPEED_ACTUAL: int
    IR_MACHINE_STATE: int
    IR_RUNTIME_SECS: int
    IR_DOWNTIME_SECS: int
    IR_THROUGHPUT_PER_HR: int
    IR_JAM_TIMER_ACC: int
    IR_ALARM_WORD: int
    IR_LAST_FAULT_CODE: int
    # Meta
    modbus_connected: bool
    poll_latency_ms: float
    server_time: str
