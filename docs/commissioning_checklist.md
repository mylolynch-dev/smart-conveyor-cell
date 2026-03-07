# Commissioning Checklist — Smart Conveyor Sorting Cell

**Project:** Smart Conveyor Sorting Cell
**Revision:** 1.0
**Date:** 2026-03-06

---

## Section 1: Pre-Power Checks (Mechanical & Electrical)

| # | Check Item | Result | Initials |
|---|---|---|---|
| 1.1 | Confirm all mechanical installation is complete and secured | PASS / FAIL | |
| 1.2 | Conveyor belt tensioned and tracking correctly | PASS / FAIL | |
| 1.3 | All sensors mechanically mounted and wired per I/O list | PASS / FAIL | |
| 1.4 | All solenoid valves mounted and pneumatic connections made | PASS / FAIL | |
| 1.5 | Control panel door closed; panel clean of debris | PASS / FAIL | |
| 1.6 | All terminal blocks torqued to spec (1.2 Nm for PT 2.5) | PASS / FAIL | |
| 1.7 | Verify 480VAC 3-phase available at MCC | PASS / FAIL | |
| 1.8 | Verify 24VDC PSU output: _____ VDC (nominal 24V ± 5%) | PASS / FAIL | |
| 1.9 | All fuses installed per BOM; check rating matches drawing | PASS / FAIL | |
| 1.10 | E-stop button: press and confirm NC circuit opens (continuity test) | PASS / FAIL | |
| 1.11 | E-stop button: release and confirm NC circuit closes | PASS / FAIL | |
| 1.12 | Verify motor rotation direction (bump test — jog momentary) | PASS / FAIL | |

---

## Section 2: I/O Loop Check — Digital Inputs

> Method: Force each input ON physically or via test tool; verify PLC tag in Run mode.

| # | Tag | Physical Action | Expected PLC State | Actual | Initials |
|---|---|---|---|---|---|
| 2.1 | IN_START_PB | Press START button | TRUE (momentary) | | |
| 2.2 | IN_STOP_PB | Press STOP button | TRUE (momentary) | | |
| 2.3 | IN_ESTOP | Press E-stop | IN_ESTOP = FALSE | | |
| 2.4 | IN_ESTOP | Release E-stop | IN_ESTOP = TRUE | | |
| 2.5 | IN_FAULT_RESET | Press FAULT RESET | TRUE (momentary) | | |
| 2.6 | IN_MODE_SELECT | Switch to MANUAL | TRUE | | |
| 2.7 | IN_MODE_SELECT | Switch to AUTO | FALSE | | |
| 2.8 | IN_MOTOR_FEEDBACK | Manually close aux contact | TRUE | | |
| 2.9 | IN_JAM_SENSOR | Block sensor with test rod | TRUE | | |
| 2.10 | IN_BOX_DETECT | Pass test object through | TRUE | | |
| 2.11 | IN_SIZE_SMALL | Break small beam | TRUE | | |
| 2.12 | IN_SIZE_LARGE | Break large beam | TRUE | | |
| 2.13 | IN_METAL_DETECT | Hold metal object at sensor | TRUE | | |
| 2.14 | IN_GATE_A_CONFIRM | Manually actuate gate A | TRUE | | |
| 2.15 | IN_GATE_B_CONFIRM | Manually actuate gate B | TRUE | | |

---

## Section 3: I/O Loop Check — Digital Outputs

> Method: Force each output ON via PLC (maintenance mode or tag force); verify physical result.

| # | Tag | Expected Physical Result | Actual | Initials |
|---|---|---|---|---|
| 3.1 | OUT_MOTOR_RUN | Motor starter coil picks up; motor runs | | |
| 3.2 | OUT_GATE_A | Gate A solenoid energizes; gate deflects | | |
| 3.3 | OUT_GATE_B | Gate B solenoid energizes; gate deflects | | |
| 3.4 | OUT_GATE_C | Gate C solenoid energizes; gate deflects | | |
| 3.5 | OUT_ALARM_HORN | Horn sounds | | |
| 3.6 | OUT_ESTOP_LIGHT | Red pilot light ON | | |
| 3.7 | OUT_FAULT_LIGHT | Amber pilot light ON | | |
| 3.8 | OUT_RUN_LIGHT | Green pilot light ON | | |

---

## Section 4: Communications Check

| # | Check Item | Result | Initials |
|---|---|---|---|
| 4.1 | Ethernet cable connected: HMI PC ↔ Switch ↔ PLC | PASS / FAIL | |
| 4.2 | Ping PLC IP address from HMI PC: `ping 127.0.0.1` | PASS / FAIL | |
| 4.3 | PLC Modbus TCP server responding on port 5020 | PASS / FAIL | |
| 4.4 | HMI backend starts without error: `python hmi/backend/app.py` | PASS / FAIL | |
| 4.5 | HMI frontend loads at http://localhost:8000 | PASS / FAIL | |
| 4.6 | WebSocket connects — status dot turns green | PASS / FAIL | |
| 4.7 | Live tags updating in browser (machine state, heartbeat) | PASS / FAIL | |
| 4.8 | Poll latency < 100ms (shown on Network Status screen) | PASS / FAIL | |
| 4.9 | SQLite database created at scada/db/conveyor.db | PASS / FAIL | |

---

## Section 5: Functional Tests — Core Logic

| # | Test | Procedure | Expected Result | Actual | Initials |
|---|---|---|---|---|---|
| 5.1 | Auto Start | Press START in AUTO mode | Motor runs; state = AUTO_RUN | | |
| 5.2 | Auto Stop | Press STOP in AUTO mode | Motor stops; state = IDLE | | |
| 5.3 | Seal-in latch | Press START; release; hold | Motor continues running | | |
| 5.4 | E-stop | Press E-stop while running | All outputs off; state = ESTOP | | |
| 5.5 | E-stop reset | Release E-stop; press RESET | State returns to IDLE | | |
| 5.6 | Jam fault | Block jam sensor > 3s while running | State = FAULT; horn; fault code 1 | | |
| 5.7 | Jam reset | Clear jam; press FAULT RESET | State returns to IDLE | | |
| 5.8 | Motor FB loss | Disable motor feedback signal | After 2s: state = FAULT; code 2 | | |
| 5.9 | Manual mode | Stop motor; switch to MANUAL | State = MANUAL | | |
| 5.10 | Mode interlock | Try to switch mode while motor runs | Mode does not change | | |
| 5.11 | Gate A routing | Present small non-metal box | OUT_GATE_A energizes | | |
| 5.12 | Gate B routing | Present metal object | OUT_GATE_B energizes | | |
| 5.13 | Gate C routing | Present large non-metal box | OUT_GATE_C energizes | | |
| 5.14 | Box counter | Run 10 boxes through | IR_BOX_COUNT_TOTAL = 10 | | |
| 5.15 | Speed setpoint | Set speed to 80% via HMI | IR_SPEED_ACTUAL ramps to 80 | | |
| 5.16 | Heartbeat | Monitor OUT_HEARTBEAT in HMI | Toggles every ~500ms | | |

---

## Section 6: HMI Acceptance

| # | Screen | Check | Result | Initials |
|---|---|---|---|---|
| 6.1 | Overview | Machine state badge updates correctly | PASS / FAIL | |
| 6.2 | Overview | Fault banner appears on fault conditions | PASS / FAIL | |
| 6.3 | Overview | Conveyor animation runs when motor on | PASS / FAIL | |
| 6.4 | Manual | Speed slider writes to PLC | PASS / FAIL | |
| 6.5 | Alarms | Alarm appears when fault triggered | PASS / FAIL | |
| 6.6 | Alarms | ACK button clears alarm from active list | PASS / FAIL | |
| 6.7 | Production | Box counts increment correctly | PASS / FAIL | |
| 6.8 | Maintenance | All sensor states reflect reality | PASS / FAIL | |
| 6.9 | Network | Modbus status shows Connected | PASS / FAIL | |

---

## Section 7: Sign-Off

| Role | Name | Signature | Date |
|---|---|---|---|
| Controls Engineer | | | |
| Electrical Technician | | | |
| Operations Supervisor | | | |
| Customer Representative | | | |

**Overall Result:** PASS / FAIL / CONDITIONAL PASS

**Conditions (if applicable):**

---

*End of Commissioning Checklist*
