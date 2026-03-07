# Tutorial — Smart Conveyor Sorting Cell

This document walks you through what the project is, what you're looking at, and how to interact with it.

---

## What is this project?

You're running a **simulated industrial factory control system**. In a real factory, a conveyor belt would move physical boxes through sensors, a PLC (Programmable Logic Controller) would read those sensors and control gates and motors, and an HMI (Human Machine Interface) screen would let operators monitor and control everything.

This project simulates all of that in software:

```
[Virtual PLC]  ←→  Modbus TCP  ←→  [HMI Backend]  ←→  WebSocket  ←→  [Your Browser]
   (Python)                          (FastAPI)                          (The website)
```

- The **PLC simulator** (`plc_sim.py`) pretends to be a real industrial PLC. It runs a scan loop every 100ms, reads virtual sensor inputs, executes logic, and updates outputs. It also runs a Modbus TCP server so other software can read/write its data.
- The **HMI backend** (`app.py`) connects to the PLC over Modbus, reads all the tag values every 500ms, and streams them live to your browser over WebSocket.
- The **browser** shows you live data updating in real time and lets you send commands back to the PLC.

---

## The Conveyor Process

Here's what the virtual conveyor does:

```
 [Box arrives]
      │
      ▼
 [Entry sensor detects box]
      │
      ▼
 [Size sensors read it]      [Metal detector reads it]
      │                             │
      ▼                             ▼
 Small box?  ──────────────────────────────► Gate A opens → Lane A
 Large box?  ──────────────────────────────► Gate C opens → Lane C
 Metal part? (highest priority) ───────────► Gate B opens → Lane B
      │
      ▼
 [Box counted, gate closes]
```

Three diverter gates physically deflect boxes off the belt into different output lanes based on what the sensors detected. Metal always wins — even a large metal box goes to Lane B.

---

## The 5 Machine States

The PLC is always in one of these 5 states. You'll see this as the colored badge on the Overview screen.

| State | Color | Meaning |
|---|---|---|
| **IDLE** | Grey | Motor stopped, system ready, waiting for Start |
| **AUTO_RUN** | Green | Motor running, conveyor moving, sorting automatically |
| **MANUAL** | Amber | Motor can be manually controlled, automatic sorting off |
| **FAULT** | Red | Something went wrong — motor stopped, needs reset |
| **ESTOP** | Red (flashing) | Emergency stop activated — everything off |

---

## Screen-by-Screen Guide

### Tab 1: Overview

This is the main operator screen. It shows everything at a glance.

**What you see:**
- **State badge** (top left) — the current machine state (IDLE/AUTO_RUN/MANUAL/FAULT/ESTOP)
- **Mode badge** — AUTO or MANUAL
- **START / STOP / RESET buttons** — the main controls
- **Four LEDs** on the right:
  - Motor Run (green when conveyor is moving)
  - E-Stop Active (red when emergency stop is pressed)
  - Fault (red when a fault is latched)
  - Alarm Horn (amber when the horn is sounding)
- **Conveyor diagram** — shows the belt with three gates (A, B, C). When running, the belt lines animate. When a box is detected, a colored rectangle appears and travels along the belt:
  - Green rectangle = small box → Gate A
  - Blue rectangle = large box → Gate C
  - Amber rectangle = metal part → Gate B
- **Four metric tiles** at the bottom:
  - Total boxes counted this shift
  - Throughput (boxes per hour, rolling average)
  - Actual conveyor speed %
  - Runtime (how long it's been running)

**How to use it:**
1. Press **▶ START** — the state badge turns green (AUTO_RUN), the belt animates, boxes start appearing
2. Press **■ STOP** — motor stops, state goes back to IDLE
3. If a fault occurs, a red banner appears at the top. Press **↺ RESET FAULT** after the cause clears

---

### Tab 2: Manual Controls

This is the maintenance/commissioning screen for direct control.

**What you see:**
- **Mode toggle** — switch between AUTO and MANUAL. The motor must be stopped before you can change modes.
- **START / STOP buttons** — same as Overview
- **Speed slider** — sets the conveyor speed from 0–100%. Drag it and watch the actual speed ramp up/down on the Overview screen. The PLC ramps speed gradually (2% per scan) rather than jumping instantly — this simulates a VFD (Variable Frequency Drive) acceleration curve.
- **Gate indicators** — shows which gates are currently open (lit up). In AUTO mode these are PLC-controlled. In MANUAL mode they still show the current state.
- **Jam Timer Preset** — how many ticks (×100ms) the jam sensor must be active before it triggers a fault. Default is 30 ticks = 3 seconds.
- **Reset Fault / Reset Shift Counters** buttons

**Try this:** Start the conveyor (AUTO_RUN), then go to Manual Controls and drag the speed slider to 20%. Watch the speed dial on Overview slowly ramp down.

---

### Tab 3: Alarms

This screen shows alarm history from the SQLite database — every fault that has occurred is logged here permanently.

**What you see:**
- **Active Alarms** panel (left) — alarms that have NOT been acknowledged yet. Each row shows:
  - Time the alarm triggered
  - Alarm code number
  - Description of what went wrong
  - Priority (HIGH / MEDIUM / LOW)
  - An **ACK** button
- **Alarm History** panel (right) — all alarms ever recorded, including acknowledged ones

**The 4 alarm types:**

| Code | Name | What caused it | What to do |
|---|---|---|---|
| 1 | Conveyor Jam | Jam sensor was active for > 3 seconds while motor was running | Clear the jam, press RESET |
| 2 | Motor Feedback Lost | Motor was commanded ON but the feedback signal didn't confirm it within 2 seconds | Check motor starter/wiring, press RESET |
| 3 | Watchdog / Comms Loss | PLC heartbeat stopped — HMI lost communication | Check network connection |
| 4 | Sensor Mismatch | Both size sensors (Small AND Large) were active at the same time | Check sensor alignment, press RESET |

**How to use it:** When an alarm appears, click **ACK** to acknowledge it. This logs a timestamp and moves it to history. The alarm still shows in history so there's a permanent record.

---

### Tab 4: Production Stats

This screen shows shift production data.

**What you see:**
- **Four count tiles** — total boxes, small (Lane A), large (Lane C), metal (Lane B)
- **Throughput** — boxes per hour calculated as a rolling average
- **OEE-Lite** — Overall Equipment Effectiveness, simplified. Formula: `Runtime ÷ (Runtime + Downtime) × 100%`. A value of 85%+ is considered good in real manufacturing. If the conveyor runs half the time and is stopped the other half, OEE = 50%.
- **Runtime bar** — green, shows how long the conveyor has been running this shift
- **Downtime bar** — red, shows time spent in FAULT, ESTOP, or IDLE
- **Speed trend chart** — shows actual speed vs. setpoint over time. The dashed line is the setpoint; the solid blue line is actual speed. You can see the ramp-up behavior when you change speed.

**Try this:** Start the conveyor, let it run a minute, then stop it. Watch the OEE drop. Then run it again and watch OEE recover.

---

### Tab 5: Maintenance

This screen is for engineers diagnosing the system — not for normal operators.

**What you see:**
- **Sensor States grid** — all 15 physical inputs shown as LEDs. When a sensor goes active, its LED lights up. This lets you verify sensors are working.
  - The **E-Stop (NC)** LED is special — it's GREEN when safe (contact closed) and RED when the e-stop is pressed. This is because E-stop is a Normally Closed (NC) contact — it's electrically closed during normal operation.
- **Jam Timer progress bar** — shows how close the jam timer is to tripping. Watch this fill up if you trigger the jam sensor.
- **Counter values table** — raw counter values, alarm word bitmask (shown in binary), speed actual/setpoint
- **Watchdog Heartbeat** — a green LED that blinks every 500ms when the PLC scan loop is running. If this stops blinking, the PLC sim has crashed.
- **Last Fault** — shows the last fault code that was latched

**Try this:** Go to Maintenance and watch the sensor states while the conveyor runs. You'll see IN_BOX_DETECT, IN_SIZE_SMALL/LARGE, IN_METAL_DETECT flicker as simulated boxes pass through.

---

### Tab 6: Network Status

This screen is for engineers monitoring the communication layer.

**What you see:**
- **Modbus TCP connection status** — green = connected to PLC simulator, red = disconnected. If you stop the PLC sim, this turns red within 2 seconds.
- **Poll Latency** — how long the last Modbus read took in milliseconds. Should be under 10ms on localhost.
- **Last Successful Read** — timestamp of the last successful Modbus poll
- **Network topology diagram** — ASCII art showing how the components connect
- **Protocol reference** — explains how real plant protocols (EtherNet/IP, PROFINET, IO-Link, DeviceNet) compare to the Modbus TCP used here

---

## Simulating Faults

Here's how to trigger each fault intentionally to see the system respond:

### Trigger a Jam Fault
The IO simulator randomly triggers jams at a very low rate (~0.1% per scan). To force one faster:
1. Start the conveyor (AUTO_RUN)
2. Go to **Manual Controls** and set the **Jam Timer Preset** slider to **5** (0.5 seconds)
3. Wait — a simulated jam will occur sooner
4. Watch: state changes to FAULT, horn activates, red banner appears, alarm is logged
5. Press **↺ RESET FAULT** on Overview to clear it

### Trigger a Motor Feedback Fault
The IO simulator simulates motor feedback with a 300ms delay. A feedback fault (code 2) would occur if the feedback was interrupted. This one is harder to trigger manually in simulation but can be observed if you watch the Maintenance screen — IN_MOTOR_FEEDBACK goes TRUE about 300ms after the motor starts.

---

## What the Ladder Logic Is Actually Doing

Every 100ms, the PLC simulator runs through these logic checks in order (like a real PLC scan):

1. **Rung 1** — Did the fault reset button just get pressed? (rising edge detection)
2. **Rung 2** — Did the E-stop just get pressed? (falling edge detection — it's NC)
3. **Rung 3** — Did the HMI send a command? (START/STOP/RESET/SHIFT_RESET via register write)
4. **Rung 4** — Update E-stop indicator light
5. **Rung 5** — Motor seal-in circuit: `Motor = (Start OR Motor) AND NOT Stop AND all permissives OK`
   - This is a classic industrial latch — once started, the motor "seals in" and keeps itself running through its own output contact
6. **Rung 6** — Jam timer: if jam sensor is active AND motor running, accumulate time. If time > preset → fault
7. **Rung 7** — Motor feedback timer: if motor commanded but no feedback for 2s → fault
8. **Rung 8** — Sensor mismatch: if both size sensors active → fault
9. **Rung 9** — Fault light output
10. **Rung 10** — Gate logic: METAL overrides everything → Gate B; else LARGE → Gate C; else SMALL → Gate A
11. **Rung 11** — Horn: sound if any fault active
12. **Rung 12** — Box counters: increment on each rising edge of the box detect sensor
13. **Rung 13** — Production complete: sound horn once when total boxes hit target (200)
14. **Rung 14** — Watchdog heartbeat: toggle a bit every 5 scans so the HMI knows the PLC is alive

---

## The Modbus Protocol Layer

When you click START in the browser, here's exactly what happens:

```
1. Browser sends:  POST /command  {"command": 1}
2. HMI backend receives it
3. HMI backend writes value 1 to Modbus Holding Register 4 (HR_HMI_COMMAND)
4. PLC simulator reads HR[4] on its next scan (100ms later)
5. PLC sees value 1 = START command, sets IN_START_PB = True internally
6. Rung 5 (seal-in circuit) fires, OUT_MOTOR_RUN = True
7. HR[4] is reset to 0 by the PLC (command consumed)
8. PLC pushes OUT_MOTOR_RUN=True into its Modbus coil register
9. HMI backend reads the coils on its next poll (500ms)
10. HMI backend sends the new tag state to the browser via WebSocket
11. Browser updates the state badge to AUTO_RUN and starts the belt animation
```

Total round-trip from button click to visual update: up to ~600ms.

---

## Quick Reference: What to Click First

If you just want to see it do something:

1. Open **http://localhost:8000**
2. Click **▶ START** on the Overview screen
3. Watch the conveyor belt animate and boxes travel across
4. Click the **Production** tab — watch box counts increment
5. Click the **Maintenance** tab — watch sensor LEDs flicker
6. Go back to **Overview**, click **■ STOP**
7. Click **▶ START** again, then go to **Alarms** tab
8. Wait for a random jam fault (or lower the jam timer preset in Manual Controls)
9. When fault appears — click **ACK** on the alarm, then go back to Overview and click **↺ RESET FAULT**
10. System returns to IDLE, ready to start again
