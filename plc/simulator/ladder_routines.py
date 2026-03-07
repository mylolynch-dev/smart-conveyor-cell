"""
Ladder logic routines for the Smart Conveyor Sorting Cell.

Each function corresponds to a rung or rung group in a real ladder logic program.
They are executed in order, once per scan cycle (100 ms), mirroring PLC scan behavior.

Concepts demonstrated:
  - Seal-in (latch) circuit
  - E-stop latch
  - Permissive interlocks
  - TON timer (jam detection, motor feedback check)
  - One-shot (rising edge detection) for fault reset
  - CTU counter (part counting per lane)
  - Diverter gate logic with priority
  - Manual / Auto mode interlock
  - Alarm bitmask
  - Watchdog heartbeat
  - Production complete cycle
"""

import time
from state_machine import MachineState, FaultCode
from tag_db import TagDB, ALARM_BIT


class TON:
    """On-delay timer. Accumulates while IN is True. Resets when IN goes False."""

    def __init__(self, preset_ticks: int = 0):
        self.preset = preset_ticks   # in scan ticks (1 tick = 100 ms)
        self.acc = 0
        self.Q = False               # timer done bit

    def scan(self, IN: bool, preset_override: int = None) -> bool:
        if preset_override is not None:
            self.preset = preset_override
        if IN:
            self.acc += 1
            self.Q = self.acc >= self.preset
        else:
            self.acc = 0
            self.Q = False
        return self.Q


class CTU:
    """Up counter. Increments on rising edge of CU. Reset by R."""

    def __init__(self, preset: int = 9999):
        self.preset = preset
        self.acc = 0
        self.Q = False
        self._prev_cu = False

    def scan(self, CU: bool, R: bool = False) -> bool:
        if R:
            self.acc = 0
            self.Q = False
        else:
            rising = CU and not self._prev_cu
            if rising:
                self.acc += 1
            self.Q = self.acc >= self.preset
        self._prev_cu = CU
        return self.Q


class RTRIG:
    """Rising edge one-shot."""

    def __init__(self):
        self._prev = False

    def scan(self, IN: bool) -> bool:
        edge = IN and not self._prev
        self._prev = IN
        return edge


class LadderRoutines:
    """
    All ladder rungs for the conveyor cell.
    Instantiate once; call execute() every scan cycle.
    """

    def __init__(self, db: TagDB, state_machine):
        self.db = db
        self.sm = state_machine

        # Timer instances
        self.jam_timer = TON()
        self.motor_fb_timer = TON()

        # Counter instances
        self.ctr_total = CTU()
        self.ctr_small = CTU()
        self.ctr_large = CTU()
        self.ctr_metal = CTU()

        # One-shot instances
        self.os_fault_reset = RTRIG()
        self.os_box_detect = RTRIG()
        self.os_box_small = RTRIG()
        self.os_box_large = RTRIG()
        self.os_box_metal = RTRIG()
        self.os_prod_complete = RTRIG()

        # Heartbeat state
        self._heartbeat = False
        self._scan_count = 0

        # Shift timing
        self._shift_start = time.time()
        self._run_start: float | None = None
        self._total_downtime = 0.0
        self._downtime_start: float | None = None

        # Production target (boxes per shift before "production complete" fires)
        self.PRODUCTION_TARGET = 200

        # Motor seal-in latch (internal bit)
        self._motor_latch = False

        # Alarm horn one-shot (so it fires once, not continuously)
        self._horn_fired = False

    # ------------------------------------------------------------------
    # Main execute — call once per scan
    # ------------------------------------------------------------------

    def execute(self) -> None:
        db = self.db
        sm = self.sm
        snap = db.snapshot()

        state = sm.state

        # ---- Rung 1: Fault reset one-shot ----------------------------
        reset_pulse = self.os_fault_reset.scan(snap["IN_FAULT_RESET"])

        # ---- Rung 2: Clear fault code on reset -----------------------
        if reset_pulse and state in (MachineState.FAULT, MachineState.ESTOP):
            db.set("HR_FAULT_CODE", FaultCode.NONE)
            snap["HR_FAULT_CODE"] = int(FaultCode.NONE)

        # ---- Rung 3: Process HMI_COMMAND register --------------------
        #   1=START 2=STOP 3=RESET 4=SHIFT_RESET
        hmi_cmd = snap["HR_HMI_COMMAND"]
        if hmi_cmd == 1:
            db.set("IN_START_PB", True)
        elif hmi_cmd == 2:
            db.set("IN_STOP_PB", True)
        elif hmi_cmd == 3:
            db.set("IN_FAULT_RESET", True)
        elif hmi_cmd == 4:
            self._reset_shift_counters()
        if hmi_cmd != 0:
            db.set("HR_HMI_COMMAND", 0)

        # Re-snapshot after HMI command side-effects
        snap = db.snapshot()

        # Run state machine NOW — while IN_START_PB / IN_STOP_PB are still set.
        # If we wait until after plc_sim.py calls sm.transition(), the momentary
        # bits have already been cleared and AUTO_RUN never fires.
        sm.transition(snap)
        state = sm.state

        # ---- Rung 4: E-stop indicator light --------------------------
        db.set("OUT_ESTOP_LIGHT", not snap["IN_ESTOP"])

        # ---- Rung 5: Motor permissives + seal-in circuit -------------
        #   Motor can run only if:
        #     - State is AUTO_RUN or MANUAL
        #     - E-stop is closed (True)
        #     - No active fault
        permissives_ok = (
            snap["IN_ESTOP"]
            and snap["HR_FAULT_CODE"] == FaultCode.NONE
            and state in (MachineState.AUTO_RUN, MachineState.MANUAL)
        )
        # Seal-in latch: (START OR latch) AND NOT STOP AND permissives
        start = snap["IN_START_PB"]
        stop = snap["IN_STOP_PB"]
        self._motor_latch = (start or self._motor_latch) and not stop and permissives_ok
        motor_run = self._motor_latch and permissives_ok

        db.set("OUT_MOTOR_RUN", motor_run)
        db.set("OUT_RUN_LIGHT", motor_run)

        # Clear momentary start/stop after processing
        db.set("IN_START_PB", False)
        db.set("IN_STOP_PB", False)

        # ---- Rung 6: Jam detection TON timer -------------------------
        jam_active = snap["IN_JAM_SENSOR"] and motor_run
        jam_preset = snap["HR_JAM_TIMER_PRESET"]
        jam_done = self.jam_timer.scan(jam_active, jam_preset)
        db.set("IR_JAM_TIMER_ACC", self.jam_timer.acc)

        if jam_done and snap["HR_FAULT_CODE"] == FaultCode.NONE:
            db.set("HR_FAULT_CODE", int(FaultCode.JAM))
            self._set_alarm_bit(FaultCode.JAM, True)

        # ---- Rung 7: Motor feedback check timer ----------------------
        fb_loss = motor_run and not snap["IN_MOTOR_FEEDBACK"]
        fb_done = self.motor_fb_timer.scan(fb_loss, preset_override=20)  # 20 ticks = 2 s
        if fb_done and snap["HR_FAULT_CODE"] == FaultCode.NONE:
            db.set("HR_FAULT_CODE", int(FaultCode.MOTOR_FEEDBACK))
            self._set_alarm_bit(FaultCode.MOTOR_FEEDBACK, True)

        # ---- Rung 8: Sensor mismatch check ---------------------------
        if snap["IN_SIZE_SMALL"] and snap["IN_SIZE_LARGE"] and snap["HR_FAULT_CODE"] == FaultCode.NONE:
            db.set("HR_FAULT_CODE", int(FaultCode.SENSOR_MISMATCH))
            self._set_alarm_bit(FaultCode.SENSOR_MISMATCH, True)

        # ---- Rung 9: Clear alarm bits on fault reset -----------------
        if reset_pulse:
            db.set("IR_ALARM_WORD", 0)
            db.set("HR_FAULT_CODE", int(FaultCode.NONE))

        # ---- Rung 10: Fault / alarm light ----------------------------
        db.set("OUT_FAULT_LIGHT", snap["HR_FAULT_CODE"] != FaultCode.NONE)

        # ---- Rung 11: Diverter gate logic ----------------------------
        #   Priority: METAL > LARGE > SMALL (default = pass-through lane)
        if motor_run and snap["IN_BOX_DETECT"]:
            metal = snap["IN_METAL_DETECT"]
            large = snap["IN_SIZE_LARGE"] and not snap["IN_SIZE_SMALL"]
            small = snap["IN_SIZE_SMALL"] and not snap["IN_SIZE_LARGE"]
            db.set("OUT_GATE_B", metal)
            db.set("OUT_GATE_C", large and not metal)
            db.set("OUT_GATE_A", small and not metal and not large)
        else:
            db.set("OUT_GATE_A", False)
            db.set("OUT_GATE_B", False)
            db.set("OUT_GATE_C", False)

        # ---- Rung 12: Part counters (CTU on rising edge of BOX_DETECT)
        shift_reset = snap["HR_SHIFT_RESET"] == 1
        if shift_reset:
            self._reset_shift_counters()
            db.set("HR_SHIFT_RESET", 0)

        box_edge = self.os_box_detect.scan(snap["IN_BOX_DETECT"] and motor_run)
        small_edge = self.os_box_small.scan(snap["IN_SIZE_SMALL"] and snap["IN_BOX_DETECT"] and motor_run)
        large_edge = self.os_box_large.scan(snap["IN_SIZE_LARGE"] and snap["IN_BOX_DETECT"] and motor_run)
        metal_edge = self.os_box_metal.scan(snap["IN_METAL_DETECT"] and snap["IN_BOX_DETECT"] and motor_run)

        self.ctr_total.scan(box_edge, R=False)
        self.ctr_small.scan(small_edge, R=False)
        self.ctr_large.scan(large_edge, R=False)
        self.ctr_metal.scan(metal_edge, R=False)

        db.set("IR_BOX_COUNT_TOTAL", self.ctr_total.acc)
        db.set("IR_BOX_COUNT_SMALL", self.ctr_small.acc)
        db.set("IR_BOX_COUNT_LARGE", self.ctr_large.acc)
        db.set("IR_BOX_COUNT_METAL", self.ctr_metal.acc)

        # ---- Rung 13: Production complete one-shot -------------------
        prod_done = self.ctr_total.acc >= self.PRODUCTION_TARGET
        if self.os_prod_complete.scan(prod_done) and not self._horn_fired:
            db.set("OUT_ALARM_HORN", True)
            self._horn_fired = True
        if not prod_done:
            self._horn_fired = False
            db.set("OUT_ALARM_HORN", False)

        # ---- Rung 14: Alarm horn for faults --------------------------
        if snap["HR_FAULT_CODE"] != FaultCode.NONE:
            db.set("OUT_ALARM_HORN", True)
        elif not prod_done:
            db.set("OUT_ALARM_HORN", False)

        # ---- Rung 15: Throughput calculation -------------------------
        elapsed = time.time() - self._shift_start
        runtime = elapsed - self._total_downtime
        if runtime > 0:
            tph = int((self.ctr_total.acc / runtime) * 3600)
        else:
            tph = 0
        db.set("IR_THROUGHPUT_PER_HR", min(tph, 9999))
        db.set("IR_RUNTIME_SECS", int(runtime))
        db.set("IR_DOWNTIME_SECS", int(self._total_downtime))

        # ---- Rung 16: Track downtime ---------------------------------
        if state in (MachineState.FAULT, MachineState.ESTOP, MachineState.IDLE):
            if self._downtime_start is None:
                self._downtime_start = time.time()
            self._total_downtime += (time.time() - self._downtime_start)
            self._downtime_start = time.time()
        else:
            self._downtime_start = None

        # ---- Rung 17: Speed actual (ramp to setpoint) ----------------
        setpoint = snap["HR_SPEED_SETPOINT"]
        actual = snap["IR_SPEED_ACTUAL"]
        if motor_run:
            if actual < setpoint:
                actual = min(actual + 2, setpoint)
            elif actual > setpoint:
                actual = max(actual - 2, setpoint)
        else:
            actual = max(actual - 5, 0)
        db.set("IR_SPEED_ACTUAL", actual)

        # ---- Rung 18: Watchdog heartbeat (toggles every scan) --------
        self._scan_count += 1
        if self._scan_count % 5 == 0:  # toggle every 5 scans = 500 ms
            self._heartbeat = not self._heartbeat
            db.set("OUT_HEARTBEAT", self._heartbeat)

        # ---- Rung 19: Machine state to IR ----------------------------
        db.set("IR_MACHINE_STATE", int(sm.state))
        db.set("IR_LAST_FAULT_CODE", int(sm.last_fault_code))

        # ---- Rung 20: Manual/Auto mode interlock ---------------------
        #   Only allow mode change when motor is stopped
        if not motor_run:
            mode_cmd = snap["HR_MODE_COMMAND"]
            if mode_cmd != snap["IN_MODE_SELECT"]:
                db.set("IN_MODE_SELECT", mode_cmd)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_alarm_bit(self, fault_code: FaultCode, active: bool) -> None:
        bit_pos = ALARM_BIT.get(int(fault_code), 0)
        current = self.db.get("IR_ALARM_WORD")
        if active:
            current |= (1 << bit_pos)
        else:
            current &= ~(1 << bit_pos)
        self.db.set("IR_ALARM_WORD", current)

    def _reset_shift_counters(self) -> None:
        self.ctr_total.acc = 0
        self.ctr_small.acc = 0
        self.ctr_large.acc = 0
        self.ctr_metal.acc = 0
        self.ctr_total.Q = False
        self._shift_start = time.time()
        self._total_downtime = 0.0
        self._downtime_start = None
        self._horn_fired = False
        db = self.db
        db.set("IR_BOX_COUNT_TOTAL", 0)
        db.set("IR_BOX_COUNT_SMALL", 0)
        db.set("IR_BOX_COUNT_LARGE", 0)
        db.set("IR_BOX_COUNT_METAL", 0)
        db.set("IR_RUNTIME_SECS", 0)
        db.set("IR_DOWNTIME_SECS", 0)
        db.set("IR_THROUGHPUT_PER_HR", 0)
