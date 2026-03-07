(* ============================================================
   Smart Conveyor Sorting Cell
   IEC 61131-3 Structured Text — OpenPLC Compatible
   File: main.st

   Import into OpenPLC Runtime via the web interface.
   Map I/O to Modbus register addresses listed below.
   ============================================================ *)

PROGRAM ConveyorSortingCell

(* ── Variable Declarations ──────────────────────────────────── *)
VAR
  (* Digital Inputs — %IX0.0 through %IX0.14 *)
  IN_START_PB       : BOOL := FALSE;   (* %IX0.0  Start pushbutton, NO *)
  IN_STOP_PB        : BOOL := FALSE;   (* %IX0.1  Stop pushbutton, NC *)
  IN_ESTOP          : BOOL := TRUE;    (* %IX0.2  E-stop, NC contact: TRUE=safe *)
  IN_FAULT_RESET    : BOOL := FALSE;   (* %IX0.3  Fault reset button *)
  IN_MODE_SELECT    : BOOL := FALSE;   (* %IX0.4  0=Auto, 1=Manual *)
  IN_MOTOR_FEEDBACK : BOOL := FALSE;   (* %IX0.5  Motor aux contact *)
  IN_JAM_SENSOR     : BOOL := FALSE;   (* %IX0.6  Jam detection sensor *)
  IN_BOX_DETECT     : BOOL := FALSE;   (* %IX0.7  Part presence — entry *)
  IN_SIZE_SMALL     : BOOL := FALSE;   (* %IX0.8  Size sensor — small *)
  IN_SIZE_LARGE     : BOOL := FALSE;   (* %IX0.9  Size sensor — large *)
  IN_METAL_DETECT   : BOOL := FALSE;   (* %IX0.10 Metal detector *)
  IN_COLOR_RED      : BOOL := FALSE;   (* %IX0.11 Color sensor — red *)
  IN_COLOR_BLUE     : BOOL := FALSE;   (* %IX0.12 Color sensor — blue *)
  IN_GATE_A_CONFIRM : BOOL := FALSE;   (* %IX0.13 Gate A position confirmation *)
  IN_GATE_B_CONFIRM : BOOL := FALSE;   (* %IX0.14 Gate B position confirmation *)

  (* Digital Outputs — %QX0.0 through %QX0.8 *)
  OUT_MOTOR_RUN     : BOOL := FALSE;   (* %QX0.0  Conveyor motor run *)
  OUT_GATE_A        : BOOL := FALSE;   (* %QX0.1  Diverter gate A — small → lane A *)
  OUT_GATE_B        : BOOL := FALSE;   (* %QX0.2  Diverter gate B — metal → lane B *)
  OUT_GATE_C        : BOOL := FALSE;   (* %QX0.3  Diverter gate C — large → lane C *)
  OUT_ALARM_HORN    : BOOL := FALSE;   (* %QX0.4  Alarm horn *)
  OUT_ESTOP_LIGHT   : BOOL := FALSE;   (* %QX0.5  E-stop indicator *)
  OUT_FAULT_LIGHT   : BOOL := FALSE;   (* %QX0.6  Fault indicator *)
  OUT_RUN_LIGHT     : BOOL := FALSE;   (* %QX0.7  Run indicator (green) *)
  OUT_HEARTBEAT     : BOOL := FALSE;   (* %QX0.8  Watchdog heartbeat *)

  (* Holding Registers — %MW0 through %MW5 *)
  HR_SPEED_SETPOINT   : INT := 60;     (* %MW0  Speed setpoint 0-100% *)
  HR_JAM_TIMER_PRESET : INT := 30;     (* %MW1  Jam timer preset (×100ms) *)
  HR_FAULT_CODE       : INT := 0;      (* %MW2  Active fault code *)
  HR_MODE_COMMAND     : INT := 0;      (* %MW3  HMI mode: 0=Auto, 1=Manual *)
  HR_HMI_COMMAND      : INT := 0;      (* %MW4  HMI command pulse *)
  HR_SHIFT_RESET      : INT := 0;      (* %MW5  Write 1 to reset counters *)

  (* Internal variables *)
  MOTOR_LATCH       : BOOL := FALSE;   (* Seal-in latch bit *)
  MACHINE_STATE     : INT  := 0;       (* 0=IDLE 1=AUTO 2=MANUAL 3=FAULT 4=ESTOP *)
  PREV_ESTOP        : BOOL := TRUE;
  PREV_FAULT_RESET  : BOOL := FALSE;
  RESET_PULSE       : BOOL := FALSE;
  ESTOP_FELL        : BOOL := FALSE;
  PERMISSIVES_OK    : BOOL := FALSE;
  HB_TICK           : INT  := 0;

  (* Counters *)
  BOX_COUNT_TOTAL   : INT := 0;
  BOX_COUNT_SMALL   : INT := 0;
  BOX_COUNT_LARGE   : INT := 0;
  BOX_COUNT_METAL   : INT := 0;
  PREV_BOX_DETECT   : BOOL := FALSE;
  PREV_SIZE_SMALL   : BOOL := FALSE;
  PREV_SIZE_LARGE   : BOOL := FALSE;
  PREV_METAL_DETECT : BOOL := FALSE;

  (* Timers *)
  JAM_TIMER         : TON;
  FB_TIMER          : TON;
END_VAR


(* ══════════════════════════════════════════════════════════════
   RUNG 1: Fault Reset One-Shot (Rising Edge)
══════════════════════════════════════════════════════════════ *)
RESET_PULSE := IN_FAULT_RESET AND NOT PREV_FAULT_RESET;
PREV_FAULT_RESET := IN_FAULT_RESET;

IF RESET_PULSE THEN
  HR_FAULT_CODE := 0;
END_IF;


(* ══════════════════════════════════════════════════════════════
   RUNG 2: E-Stop Falling Edge Detection
══════════════════════════════════════════════════════════════ *)
ESTOP_FELL := PREV_ESTOP AND NOT IN_ESTOP;
PREV_ESTOP := IN_ESTOP;


(* ══════════════════════════════════════════════════════════════
   RUNG 3: State Machine Transitions
══════════════════════════════════════════════════════════════ *)

(* E-STOP override — highest priority *)
IF ESTOP_FELL OR (NOT IN_ESTOP AND MACHINE_STATE <> 4 AND MACHINE_STATE <> 0) THEN
  MACHINE_STATE := 4;   (* ESTOP *)

ELSIF HR_FAULT_CODE <> 0 AND (MACHINE_STATE = 1 OR MACHINE_STATE = 2) THEN
  MACHINE_STATE := 3;   (* FAULT *)

ELSIF MACHINE_STATE = 0 THEN   (* IDLE *)
  IF HR_MODE_COMMAND = 1 THEN
    MACHINE_STATE := 2;   (* → MANUAL *)
  ELSIF IN_START_PB AND IN_ESTOP AND HR_FAULT_CODE = 0 THEN
    MACHINE_STATE := 1;   (* → AUTO_RUN *)
  END_IF;

ELSIF MACHINE_STATE = 1 THEN   (* AUTO_RUN *)
  IF IN_STOP_PB THEN
    MACHINE_STATE := 0;   (* → IDLE *)
  END_IF;

ELSIF MACHINE_STATE = 2 THEN   (* MANUAL *)
  IF NOT IN_ESTOP THEN
    MACHINE_STATE := 4;   (* → ESTOP *)
  ELSIF IN_STOP_PB OR HR_MODE_COMMAND = 0 THEN
    MACHINE_STATE := 0;   (* → IDLE *)
  END_IF;

ELSIF MACHINE_STATE = 3 THEN   (* FAULT *)
  IF RESET_PULSE AND HR_FAULT_CODE = 0 THEN
    MACHINE_STATE := 0;   (* → IDLE *)
  END_IF;

ELSIF MACHINE_STATE = 4 THEN   (* ESTOP *)
  IF IN_ESTOP AND RESET_PULSE THEN
    MACHINE_STATE := 0;   (* → IDLE *)
    HR_FAULT_CODE := 0;
  END_IF;
END_IF;

(* Clear momentary bits after state machine processes them *)
IN_START_PB := FALSE;
IN_STOP_PB  := FALSE;


(* ══════════════════════════════════════════════════════════════
   RUNG 4: E-Stop Indicator Light
══════════════════════════════════════════════════════════════ *)
OUT_ESTOP_LIGHT := NOT IN_ESTOP;


(* ══════════════════════════════════════════════════════════════
   RUNG 5: Motor Permissives + Seal-In Circuit
   OUT_MOTOR_RUN = (IN_START_PB OR MOTOR_LATCH) AND
                   NOT IN_STOP_PB AND IN_ESTOP AND
                   (STATE=AUTO OR STATE=MANUAL) AND
                   FAULT_CODE=0
══════════════════════════════════════════════════════════════ *)
PERMISSIVES_OK :=
  IN_ESTOP AND
  HR_FAULT_CODE = 0 AND
  (MACHINE_STATE = 1 OR MACHINE_STATE = 2);

MOTOR_LATCH := (IN_START_PB OR MOTOR_LATCH) AND
               NOT IN_STOP_PB AND
               PERMISSIVES_OK;

OUT_MOTOR_RUN := MOTOR_LATCH AND PERMISSIVES_OK;
OUT_RUN_LIGHT := OUT_MOTOR_RUN;


(* ══════════════════════════════════════════════════════════════
   RUNG 6: Jam Detection TON Timer
   Jam timer runs while jam sensor is active AND motor is running.
   On timeout → set fault code 1 (JAM)
══════════════════════════════════════════════════════════════ *)
JAM_TIMER(IN := IN_JAM_SENSOR AND OUT_MOTOR_RUN,
          PT  := T#100MS * HR_JAM_TIMER_PRESET);

IF JAM_TIMER.Q AND HR_FAULT_CODE = 0 THEN
  HR_FAULT_CODE := 1;   (* JAM fault *)
END_IF;


(* ══════════════════════════════════════════════════════════════
   RUNG 7: Motor Feedback Loss Check
   If run command is ON but feedback is OFF for > 2 seconds → fault 2
══════════════════════════════════════════════════════════════ *)
FB_TIMER(IN := OUT_MOTOR_RUN AND NOT IN_MOTOR_FEEDBACK,
         PT  := T#2S);

IF FB_TIMER.Q AND HR_FAULT_CODE = 0 THEN
  HR_FAULT_CODE := 2;   (* Motor feedback loss *)
END_IF;


(* ══════════════════════════════════════════════════════════════
   RUNG 8: Sensor Mismatch Check
   Both size sensors active simultaneously → fault 4
══════════════════════════════════════════════════════════════ *)
IF IN_SIZE_SMALL AND IN_SIZE_LARGE AND HR_FAULT_CODE = 0 THEN
  HR_FAULT_CODE := 4;   (* Sensor mismatch *)
END_IF;


(* ══════════════════════════════════════════════════════════════
   RUNG 9: Fault and Run Indicator Lights
══════════════════════════════════════════════════════════════ *)
OUT_FAULT_LIGHT := HR_FAULT_CODE <> 0;


(* ══════════════════════════════════════════════════════════════
   RUNG 10: Diverter Gate Logic
   Priority: METAL (B) > LARGE (C) > SMALL (A) > pass-through
   Gates only active when motor running AND box detected
══════════════════════════════════════════════════════════════ *)
IF OUT_MOTOR_RUN AND IN_BOX_DETECT THEN
  OUT_GATE_B := IN_METAL_DETECT;
  OUT_GATE_C := IN_SIZE_LARGE AND NOT IN_SIZE_SMALL AND NOT IN_METAL_DETECT;
  OUT_GATE_A := IN_SIZE_SMALL AND NOT IN_SIZE_LARGE AND NOT IN_METAL_DETECT;
ELSE
  OUT_GATE_A := FALSE;
  OUT_GATE_B := FALSE;
  OUT_GATE_C := FALSE;
END_IF;


(* ══════════════════════════════════════════════════════════════
   RUNG 11: Part Counters (CTU — count on rising edge of BOX_DETECT)
══════════════════════════════════════════════════════════════ *)
(* Reset counters if HR_SHIFT_RESET written *)
IF HR_SHIFT_RESET = 1 THEN
  BOX_COUNT_TOTAL := 0;
  BOX_COUNT_SMALL := 0;
  BOX_COUNT_LARGE := 0;
  BOX_COUNT_METAL := 0;
  HR_SHIFT_RESET  := 0;
END_IF;

(* Count rising edges — total *)
IF IN_BOX_DETECT AND OUT_MOTOR_RUN AND NOT PREV_BOX_DETECT THEN
  BOX_COUNT_TOTAL := BOX_COUNT_TOTAL + 1;
END_IF;

(* Count by type on rising edge of type sensor + box present *)
IF IN_SIZE_SMALL AND IN_BOX_DETECT AND OUT_MOTOR_RUN AND NOT PREV_SIZE_SMALL THEN
  BOX_COUNT_SMALL := BOX_COUNT_SMALL + 1;
END_IF;
IF IN_SIZE_LARGE AND IN_BOX_DETECT AND OUT_MOTOR_RUN AND NOT PREV_SIZE_LARGE THEN
  BOX_COUNT_LARGE := BOX_COUNT_LARGE + 1;
END_IF;
IF IN_METAL_DETECT AND IN_BOX_DETECT AND OUT_MOTOR_RUN AND NOT PREV_METAL_DETECT THEN
  BOX_COUNT_METAL := BOX_COUNT_METAL + 1;
END_IF;

(* Update previous values for edge detection *)
PREV_BOX_DETECT   := IN_BOX_DETECT AND OUT_MOTOR_RUN;
PREV_SIZE_SMALL   := IN_SIZE_SMALL AND IN_BOX_DETECT AND OUT_MOTOR_RUN;
PREV_SIZE_LARGE   := IN_SIZE_LARGE AND IN_BOX_DETECT AND OUT_MOTOR_RUN;
PREV_METAL_DETECT := IN_METAL_DETECT AND IN_BOX_DETECT AND OUT_MOTOR_RUN;


(* ══════════════════════════════════════════════════════════════
   RUNG 12: Alarm Horn
   Horn active on any fault or E-stop
══════════════════════════════════════════════════════════════ *)
OUT_ALARM_HORN := (HR_FAULT_CODE <> 0) OR (MACHINE_STATE = 4);


(* ══════════════════════════════════════════════════════════════
   RUNG 13: Watchdog Heartbeat
   Toggles every 5 scans to indicate PLC is running
══════════════════════════════════════════════════════════════ *)
HB_TICK := HB_TICK + 1;
IF HB_TICK >= 5 THEN
  OUT_HEARTBEAT := NOT OUT_HEARTBEAT;
  HB_TICK := 0;
END_IF;


(* ══════════════════════════════════════════════════════════════
   RUNG 14: Mode Interlock
   Mode change only permitted when motor is stopped
══════════════════════════════════════════════════════════════ *)
(* Mode change is handled in the state machine above *)
(* No additional rung needed — MACHINE_STATE transitions enforce it *)

END_PROGRAM
