# Controls Narrative — Smart Conveyor Sorting Cell

**Document:** Controls Narrative / Sequence of Operation
**Project:** Smart Conveyor Sorting Cell
**Revision:** 1.0
**Date:** 2026-03-06

---

## 1. System Overview

The Smart Conveyor Sorting Cell is an automated material handling system designed to sort incoming boxes by size (small/large) and material (metal/non-metal) and route them to three distinct output lanes. The system is controlled by a PLC executing IEC 61131-3 ladder logic with a 100 ms scan cycle. An HMI/SCADA system provides operator visualization, control, and alarm management over Modbus TCP.

**Conveyor lanes:**
- **Lane A** — Small non-metal boxes
- **Lane B** — Metal parts (any size)
- **Lane C** — Large non-metal boxes
- **Pass-through** — Undetected / non-sorted items

---

## 2. Equipment Description

| Component | Description |
|---|---|
| Conveyor | Belt conveyor, 5m length, variable speed VFD-driven |
| Motor | 3-phase induction motor, 2HP, 480VAC |
| VFD | Allen-Bradley PowerFlex 40, speed setpoint via Modbus |
| Entry sensor | Diffuse photoelectric — detects box presence |
| Size sensors | Through-beam pair — small/large detection |
| Metal detector | Inductive proximity sensor |
| Color sensor | RGB digital output sensor |
| Diverter gates A/B/C | Pneumatic solenoid-actuated deflectors |
| Control panel | NEMA 12 enclosure, 24VDC I/O, 480VAC motor circuit |
| PLC | ControlLogix L83E (simulation: OpenPLC) |
| HMI | FastAPI + browser HMI (simulation: Ignition for production) |

---

## 3. Operating Modes

### 3.1 Auto Mode
Normal production mode. All sorting logic is fully automatic. Operator interaction is limited to Start, Stop, Fault Reset, and speed setpoint adjustment. Diverter gates are controlled entirely by PLC logic.

### 3.2 Manual Mode
Maintenance and commissioning mode. Motor can be jogged. Individual outputs can be exercised from the HMI Manual Controls screen. Mode change is interlocked — motor must be stopped before switching modes.

### 3.3 E-Stop Mode
Initiated by any E-stop device in the safety circuit. All outputs de-energize immediately (fail-safe). Cannot be cleared until the E-stop is released and a fault reset is issued.

### 3.4 Fault Mode
Entered when a latching fault condition is detected. Motor stops; alarm horn activates. Operator must investigate cause, clear the fault condition, then issue a Fault Reset.

---

## 4. Sequence of Operation

### 4.1 System Startup
1. Power is applied to control panel. PLC begins executing in RUN mode.
2. All outputs are de-energized. Machine state: **IDLE**.
3. HMI connects via Modbus TCP. Operator verifies no active alarms.
4. Operator confirms E-stop devices are released and safety circuit is healthy.

### 4.2 Normal Auto Start
1. Operator verifies mode is **AUTO** on mode selector switch or HMI.
2. Operator presses **START** pushbutton (or HMI Start).
3. PLC verifies permissives:
   - E-stop contact closed (IN_ESTOP = TRUE)
   - No active fault code (HR_FAULT_CODE = 0)
   - Mode = Auto (MACHINE_STATE = 0, then transitions to 1)
4. PLC energizes **OUT_MOTOR_RUN**. Motor starter coil closes.
5. Motor runs up to speed. VFD accelerates to speed setpoint.
6. **IN_MOTOR_FEEDBACK** (aux contact) closes within ~300 ms. PLC verifies feedback.
7. Machine state transitions to **AUTO_RUN**.
8. Green run light illuminates. HMI state badge shows AUTO_RUN.

### 4.3 Box Sorting Cycle
1. Box placed on conveyor entry. **IN_BOX_DETECT** goes TRUE.
2. Sensors read box attributes:
   - IN_SIZE_SMALL / IN_SIZE_LARGE (size)
   - IN_METAL_DETECT (metal presence)
   - IN_COLOR_RED / IN_COLOR_BLUE (color — informational)
3. PLC applies diverter gate logic (priority: metal > large > small):
   - Metal detected → **OUT_GATE_B** energizes → box routed to Lane B
   - Large (non-metal) → **OUT_GATE_C** energizes → box routed to Lane C
   - Small (non-metal) → **OUT_GATE_A** energizes → box routed to Lane A
4. Box passes through gate zone. Gate confirmation feedback (IN_GATE_A/B_CONFIRM) verifies position.
5. Box exits. Box present sensor clears. Gates de-energize (spring return).
6. BOX_COUNT_TOTAL and appropriate lane counter increment.
7. Throughput (boxes/hr) is calculated rolling.

### 4.4 Normal Stop
1. Operator presses **STOP** pushbutton (or HMI Stop).
2. Motor seal-in latch clears.
3. **OUT_MOTOR_RUN** de-energizes.
4. VFD decelerates motor to zero.
5. Machine state transitions to **IDLE**.
6. All gates return to home (de-energized).

### 4.5 Fault: Conveyor Jam
1. Box stops on conveyor while motor runs. **IN_JAM_SENSOR** goes TRUE.
2. Jam detection TON timer begins accumulating (preset: 3.0 s default).
3. If jam sensor remains active until timer expires: **HR_FAULT_CODE = 1** is set.
4. Machine transitions to **FAULT**. Motor stops. Alarm horn sounds.
5. Operator investigates. Clears jam. Verifies jam sensor clears.
6. Operator presses **FAULT RESET**.
7. PLC verifies HR_FAULT_CODE = 0 (jam cleared) and IN_FAULT_RESET rising edge.
8. Machine transitions to **IDLE**. System ready for restart.

### 4.6 Fault: Motor Feedback Loss
1. Motor run command energized. Auxiliary contact does not close within 2 seconds.
2. FB_TIMER expires: **HR_FAULT_CODE = 2**.
3. Machine transitions to **FAULT**. Motor command de-energized.
4. Operator checks motor starter, overload relay, 480VAC power, VFD fault.
5. After correcting cause: FAULT RESET clears condition. Restart.

### 4.7 Emergency Stop
1. E-stop button pressed. NC safety circuit opens. **IN_ESTOP = FALSE**.
2. PLC detects falling edge of IN_ESTOP.
3. Machine immediately transitions to **ESTOP** — highest priority.
4. All outputs de-energized. Horn activates. Red E-stop light illuminates.
5. Operator investigates. E-stop hazard cleared. E-stop button released/reset.
6. Operator presses **FAULT RESET**.
7. Machine transitions to **IDLE** (requires both E-stop released AND reset).

---

## 5. Permissive Interlocks

For motor to run, ALL of the following must be TRUE:

| Permissive | Condition Required |
|---|---|
| E-stop circuit | IN_ESTOP = TRUE (NC contact closed = safe) |
| Fault clear | HR_FAULT_CODE = 0 (no active fault) |
| Mode active | Machine state = AUTO_RUN or MANUAL |
| Stop clear | IN_STOP_PB = FALSE (stop not pressed) |

---

## 6. Alarm Priorities

| Priority | Response Time | Operator Action Required |
|---|---|---|
| CRITICAL | Immediate | Investigate before any restart |
| HIGH | < 1 minute | Must be acknowledged and cleared |
| MEDIUM | < 5 minutes | Acknowledge; plan corrective action |
| LOW | < shift end | Log and review at shift end |

---

## 7. Production Targets and Shift Management

- **Production target:** 200 boxes per shift (configurable in code)
- At target reached: alarm horn fires once; production complete bit set
- Shift counters reset via HMI Shift Reset or HR_SHIFT_RESET register
- SCADA logs shift summary to SQLite database on each shift reset
- OEE-lite metric: Runtime ÷ (Runtime + Downtime) × 100%
