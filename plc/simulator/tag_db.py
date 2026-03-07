"""
In-memory tag database and Modbus register map.

Modbus address spaces:
  Coils         (0x)  — digital outputs, PLC writes
  Discrete Inputs (1x) — digital inputs from field
  Holding Registers (4x) — R/W: HMI writes setpoints
  Input Registers  (3x) — read-only status from PLC

All coil/register values stored here are the authoritative source of truth.
The pymodbus datastore is kept in sync by plc_sim.py after every scan.
"""

import threading


# ---------------------------------------------------------------------------
# Coil addresses (digital outputs)
# ---------------------------------------------------------------------------
COIL = {
    "OUT_MOTOR_RUN":   0,
    "OUT_GATE_A":      1,   # Diverter gate A — small boxes → lane A
    "OUT_GATE_B":      2,   # Diverter gate B — metal parts → lane B
    "OUT_GATE_C":      3,   # Diverter gate C — large boxes → lane C
    "OUT_ALARM_HORN":  4,
    "OUT_ESTOP_LIGHT": 5,
    "OUT_FAULT_LIGHT": 6,
    "OUT_RUN_LIGHT":   7,
    "OUT_HEARTBEAT":   8,
}

# ---------------------------------------------------------------------------
# Discrete input addresses (digital inputs from field / simulation)
# ---------------------------------------------------------------------------
DI = {
    "IN_START_PB":       0,
    "IN_STOP_PB":        1,
    "IN_ESTOP":          2,   # NC contact — True = safe, False = E-STOP pressed
    "IN_FAULT_RESET":    3,
    "IN_MODE_SELECT":    4,   # 0 = Auto, 1 = Manual
    "IN_MOTOR_FEEDBACK": 5,   # Motor auxiliary contact
    "IN_JAM_SENSOR":     6,
    "IN_BOX_DETECT":     7,   # Part presence at entry
    "IN_SIZE_SMALL":     8,
    "IN_SIZE_LARGE":     9,
    "IN_METAL_DETECT":  10,
    "IN_COLOR_RED":     11,
    "IN_COLOR_BLUE":    12,
    "IN_GATE_A_CONFIRM":13,
    "IN_GATE_B_CONFIRM":14,
}

# ---------------------------------------------------------------------------
# Holding register addresses (R/W — HMI can write these)
# ---------------------------------------------------------------------------
HR = {
    "HR_SPEED_SETPOINT":    0,   # 0–100 %
    "HR_JAM_TIMER_PRESET":  1,   # ticks (100 ms each); default 30 = 3 s
    "HR_FAULT_CODE":        2,   # active fault (0 = none)
    "HR_MODE_COMMAND":      3,   # 0 = Auto, 1 = Manual (HMI override)
    "HR_HMI_COMMAND":       4,   # pulse: 1=START 2=STOP 3=RESET 4=SHIFT_RESET
    "HR_SHIFT_RESET":       5,   # write 1 to reset shift counters
}

# ---------------------------------------------------------------------------
# Input register addresses (read-only status)
# ---------------------------------------------------------------------------
IR = {
    "IR_BOX_COUNT_TOTAL":   0,
    "IR_BOX_COUNT_SMALL":   1,
    "IR_BOX_COUNT_LARGE":   2,
    "IR_BOX_COUNT_METAL":   3,
    "IR_SPEED_ACTUAL":      4,
    "IR_MACHINE_STATE":     5,
    "IR_RUNTIME_SECS":      6,
    "IR_DOWNTIME_SECS":     7,
    "IR_THROUGHPUT_PER_HR": 8,
    "IR_JAM_TIMER_ACC":     9,
    "IR_ALARM_WORD":        10,   # bitmask: bit N = fault code N active
    "IR_LAST_FAULT_CODE":   11,
}

# Alarm bitmask positions (match FaultCode values)
ALARM_BIT = {1: 0, 2: 1, 3: 2, 4: 3}  # fault_code → bit position


class TagDB:
    """
    Thread-safe in-memory tag store.
    Exposes named tag access; also exports flat arrays for pymodbus sync.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Coils — 16 slots
        self._coils = [False] * 16

        # Discrete inputs — 16 slots
        self._di = [False] * 16
        self._di[DI["IN_ESTOP"]] = True   # NC contact: safe by default

        # Holding registers — 16 slots
        self._hr = [0] * 16
        self._hr[HR["HR_SPEED_SETPOINT"]] = 60    # default 60 %
        self._hr[HR["HR_JAM_TIMER_PRESET"]] = 30  # 3.0 s

        # Input registers — 16 slots
        self._ir = [0] * 16

    # ------------------------------------------------------------------
    # Generic get/set by tag name
    # ------------------------------------------------------------------

    def get(self, tag: str):
        with self._lock:
            if tag in COIL:
                return self._coils[COIL[tag]]
            if tag in DI:
                return self._di[DI[tag]]
            if tag in HR:
                return self._hr[HR[tag]]
            if tag in IR:
                return self._ir[IR[tag]]
            raise KeyError(f"Unknown tag: {tag}")

    def set(self, tag: str, value) -> None:
        with self._lock:
            if tag in COIL:
                self._coils[COIL[tag]] = bool(value)
            elif tag in DI:
                self._di[DI[tag]] = bool(value)
            elif tag in HR:
                self._hr[HR[tag]] = int(value)
            elif tag in IR:
                self._ir[IR[tag]] = int(value)
            else:
                raise KeyError(f"Unknown tag: {tag}")

    def snapshot(self) -> dict:
        """Return a full copy of all tags as a flat dict."""
        with self._lock:
            snap = {}
            for name, idx in COIL.items():
                snap[name] = self._coils[idx]
            for name, idx in DI.items():
                snap[name] = self._di[idx]
            for name, idx in HR.items():
                snap[name] = self._hr[idx]
            for name, idx in IR.items():
                snap[name] = self._ir[idx]
            return snap

    # ------------------------------------------------------------------
    # Flat array accessors for pymodbus datastore sync
    # ------------------------------------------------------------------

    def coils_list(self):
        with self._lock:
            return list(self._coils)

    def di_list(self):
        with self._lock:
            return list(self._di)

    def hr_list(self):
        with self._lock:
            return list(self._hr)

    def ir_list(self):
        with self._lock:
            return list(self._ir)

    def apply_hr_from_modbus(self, values: list) -> None:
        """Called after each scan to pull any HMI writes from the Modbus datastore."""
        with self._lock:
            for i, v in enumerate(values[:len(self._hr)]):
                self._hr[i] = int(v)

    def apply_di_from_sim(self, values: list) -> None:
        """Push simulated sensor values into DI bank."""
        with self._lock:
            for i, v in enumerate(values[:len(self._di)]):
                self._di[i] = bool(v)
