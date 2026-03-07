# FAT / SAT Test Sheet — Smart Conveyor Sorting Cell

**Factory Acceptance Test (FAT)** — performed at integrator facility before shipment
**Site Acceptance Test (SAT)** — performed at customer facility after installation

---

## FAT Test Record

**Date:** _______________
**Location:** Integrator facility / staging
**PLC firmware:** _______________
**HMI version:** 1.0
**Tested by:** _______________
**Witnessed by (Customer):** _______________

---

### FAT-01: Power-Up and Communication

| Step | Action | Expected | FAT Result | SAT Result |
|---|---|---|---|---|
| 1 | Apply 24VDC control power | All output indicators OFF; PLC in RUN | PASS / FAIL | PASS / FAIL |
| 2 | Start PLC simulator `python plc_sim.py` | "Modbus server listening on :5020" logged | PASS / FAIL | PASS / FAIL |
| 3 | Start HMI backend `python app.py` | "Uvicorn running on http://localhost:8000" | PASS / FAIL | PASS / FAIL |
| 4 | Open browser to http://localhost:8000 | HMI loads; connection dot turns green | PASS / FAIL | PASS / FAIL |
| 5 | Check Network Status screen | Modbus: Connected; Latency < 100ms | PASS / FAIL | PASS / FAIL |

---

### FAT-02: State Machine — Normal Operation

| Step | Action | Expected | FAT Result | SAT Result |
|---|---|---|---|---|
| 1 | Verify initial state | State badge = IDLE; motor stopped | PASS / FAIL | PASS / FAIL |
| 2 | Press START | State = AUTO_RUN; motor runs; green light ON | PASS / FAIL | PASS / FAIL |
| 3 | Verify motor feedback | IN_MOTOR_FEEDBACK = TRUE within 500ms | PASS / FAIL | PASS / FAIL |
| 4 | Press STOP | State = IDLE; motor stops; green light OFF | PASS / FAIL | PASS / FAIL |
| 5 | Verify seal-in | START → release button → motor stays ON | PASS / FAIL | PASS / FAIL |
| 6 | Switch to MANUAL (motor stopped) | State = MANUAL; mode badge = MANUAL | PASS / FAIL | PASS / FAIL |
| 7 | Switch back to AUTO | State = IDLE; mode badge = AUTO | PASS / FAIL | PASS / FAIL |
| 8 | Try mode change while running | Mode does NOT change (interlock) | PASS / FAIL | PASS / FAIL |

---

### FAT-03: E-Stop

| Step | Action | Expected | FAT Result | SAT Result |
|---|---|---|---|---|
| 1 | Start conveyor (AUTO_RUN) | Motor running | PASS / FAIL | PASS / FAIL |
| 2 | Press E-stop | Immediate: motor stops; state = ESTOP; horn; red light | PASS / FAIL | PASS / FAIL |
| 3 | Verify all outputs | All digital outputs de-energized | PASS / FAIL | PASS / FAIL |
| 4 | Verify fault banner | HMI shows ESTOP banner | PASS / FAIL | PASS / FAIL |
| 5 | Release E-stop only | State remains ESTOP (reset not yet pressed) | PASS / FAIL | PASS / FAIL |
| 6 | Press FAULT RESET | State = IDLE; horn off; ready to restart | PASS / FAIL | PASS / FAIL |

---

### FAT-04: Jam Detection Fault

| Step | Action | Expected | FAT Result | SAT Result |
|---|---|---|---|---|
| 1 | Start conveyor | AUTO_RUN | PASS / FAIL | PASS / FAIL |
| 2 | Activate IN_JAM_SENSOR | Jam timer begins accumulating | PASS / FAIL | PASS / FAIL |
| 3 | Wait until timer expires (3s default) | State = FAULT; fault code = 1; horn | PASS / FAIL | PASS / FAIL |
| 4 | Verify HMI alarm | Alarm appears in Active Alarms table | PASS / FAIL | PASS / FAIL |
| 5 | Clear jam sensor | Jam condition removed | PASS / FAIL | PASS / FAIL |
| 6 | Press FAULT RESET | State = IDLE; alarm clears | PASS / FAIL | PASS / FAIL |
| 7 | Acknowledge alarm in HMI | Alarm moves to history; ACK timestamp set | PASS / FAIL | PASS / FAIL |

---

### FAT-05: Motor Feedback Loss Fault

| Step | Action | Expected | FAT Result | SAT Result |
|---|---|---|---|---|
| 1 | Start conveyor | AUTO_RUN; IN_MOTOR_FEEDBACK = TRUE | PASS / FAIL | PASS / FAIL |
| 2 | Disable motor feedback signal | IN_MOTOR_FEEDBACK = FALSE | PASS / FAIL | PASS / FAIL |
| 3 | Wait 2 seconds | State = FAULT; fault code = 2 | PASS / FAIL | PASS / FAIL |
| 4 | Restore feedback; press RESET | State = IDLE | PASS / FAIL | PASS / FAIL |

---

### FAT-06: Sorting / Diverter Gate Logic

| Step | Box Type | Expected Gate | Lane | FAT Result | SAT Result |
|---|---|---|---|---|---|
| 1 | Small non-metal | Gate A | Lane A | PASS / FAIL | PASS / FAIL |
| 2 | Large non-metal | Gate C | Lane C | PASS / FAIL | PASS / FAIL |
| 3 | Metal (any size) | Gate B | Lane B | PASS / FAIL | PASS / FAIL |
| 4 | Metal + Large | Gate B (metal priority) | Lane B | PASS / FAIL | PASS / FAIL |
| 5 | No sensor active | All gates closed | Pass-through | PASS / FAIL | PASS / FAIL |
| 6 | Motor stopped | All gates closed | N/A | PASS / FAIL | PASS / FAIL |

---

### FAT-07: Production Counting and SCADA Logging

| Step | Action | Expected | FAT Result | SAT Result |
|---|---|---|---|---|
| 1 | Run 10 boxes | IR_BOX_COUNT_TOTAL = 10 | PASS / FAIL | PASS / FAIL |
| 2 | Mix small/large/metal | Lane counts match types | PASS / FAIL | PASS / FAIL |
| 3 | Check SQLite alarms table | Fault alarm records exist from tests above | PASS / FAIL | PASS / FAIL |
| 4 | Check events table | State changes logged with timestamps | PASS / FAIL | PASS / FAIL |
| 5 | Check speed_trend table | Speed samples logged every 10s | PASS / FAIL | PASS / FAIL |
| 6 | Press Shift Reset | All counters return to 0 | PASS / FAIL | PASS / FAIL |

---

### FAT-08: HMI Screens

| Step | Screen | Item | Expected | FAT Result | SAT Result |
|---|---|---|---|---|---|
| 1 | Overview | State badge | Updates with all state changes | PASS / FAIL | PASS / FAIL |
| 2 | Overview | Conveyor animation | Belt animates when motor on | PASS / FAIL | PASS / FAIL |
| 3 | Manual | Speed slider | Writes to PLC; actual speed ramps | PASS / FAIL | PASS / FAIL |
| 4 | Alarms | Active table | Shows during fault; clears on reset | PASS / FAIL | PASS / FAIL |
| 5 | Production | OEE-lite | Calculates runtime ÷ total time | PASS / FAIL | PASS / FAIL |
| 6 | Maintenance | Sensor grid | All 15 sensor states visible | PASS / FAIL | PASS / FAIL |
| 7 | Maintenance | Heartbeat | Blinks every 500ms | PASS / FAIL | PASS / FAIL |
| 8 | Network | Status | Connected; latency shown | PASS / FAIL | PASS / FAIL |

---

## Test Summary

| Test Section | FAT Result | SAT Result |
|---|---|---|
| FAT-01: Power-Up and Communication | PASS / FAIL | PASS / FAIL |
| FAT-02: Normal Operation | PASS / FAIL | PASS / FAIL |
| FAT-03: E-Stop | PASS / FAIL | PASS / FAIL |
| FAT-04: Jam Detection | PASS / FAIL | PASS / FAIL |
| FAT-05: Motor Feedback Loss | PASS / FAIL | PASS / FAIL |
| FAT-06: Sorting Logic | PASS / FAIL | PASS / FAIL |
| FAT-07: Production / SCADA | PASS / FAIL | PASS / FAIL |
| FAT-08: HMI Screens | PASS / FAIL | PASS / FAIL |
| **OVERALL** | **PASS / FAIL** | **PASS / FAIL** |

---

## Punch List (Open Items)

| # | Issue | Responsible | Target Date | Status |
|---|---|---|---|---|
| | | | | |

---

## FAT Sign-Off

| Role | Name | Signature | Date |
|---|---|---|---|
| Controls Engineer | | | |
| Customer Representative | | | |

## SAT Sign-Off

| Role | Name | Signature | Date |
|---|---|---|---|
| Controls Engineer | | | |
| Site Supervisor | | | |
| Customer Representative | | | |
