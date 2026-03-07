# Smart Conveyor Sorting Cell

A complete virtual industrial automation portfolio project demonstrating PLC ladder logic, HMI/SCADA, Modbus TCP communications, and controls engineering documentation.

---

## What This Project Demonstrates

| Skill | Implementation |
|---|---|
| **PLC Programming** | IEC 61131-3 ladder logic (14 rungs), seal-in circuits, interlocks, timers, counters, one-shots, fault latching, watchdog |
| **HMI / SCADA** | 6-screen browser HMI with live WebSocket tag stream, alarm ACK, trend charts |
| **Industrial Protocols** | Modbus TCP server + client, full register map (coils, DI, HR, IR), command writes |
| **Manufacturing Logic** | 5-state machine (IDLE/AUTO/MANUAL/FAULT/ESTOP), sorting logic with 3 diverter gates, production counting |
| **SCADA Data Layer** | SQLite historian: alarms with timestamps, events log, production snapshots, speed trend, OEE-lite |
| **Controls Documentation** | I/O list, BOM, alarm list, cause/effect matrix, commissioning checklist, FAT/SAT test sheet, network diagram, panel layout |
| **OpenPLC** | Full IEC 61131-3 Structured Text export (`plc/ladder_logic/main.st`) importable into OpenPLC Runtime |

---

## Architecture

```
Browser (HMI Frontend)
    │ HTTP / WebSocket port 8000
    ▼
HMI Backend (FastAPI)  ──── SQLite (SCADA historian)
    │ Modbus TCP port 5020 (500ms poll)
    ▼
PLC Simulator (pymodbus server)
    ├── 100ms scan cycle
    ├── I/O Simulator (sensors, motor feedback, boxes)
    ├── Ladder Routines (14 rungs)
    └── State Machine (5 states, 4 fault codes)
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- pip

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the PLC simulator (Terminal 1)
```bash
cd plc/simulator
python plc_sim.py
```
Output: `Modbus server listening on 0.0.0.0:5020`

### 3. Start the HMI backend (Terminal 2)
```bash
cd hmi/backend
python app.py
```
Output: `Uvicorn running on http://localhost:8000`

### 4. Open the HMI
Navigate to **http://localhost:8000** in any browser.

### Windows one-click launcher
```
double-click start_all.bat
```

---

## Ladder Logic Rungs

All 14 rungs implemented in `plc/simulator/ladder_routines.py` and exported to IEC 61131-3 in `plc/ladder_logic/main.st`:

| Rung | Function | Concept |
|---|---|---|
| 1 | Fault reset edge detection | One-shot (RTRIG) |
| 2 | E-stop falling edge | One-shot (FTRIG) |
| 3 | HMI command register processing | Register-based command |
| 4 | E-stop indicator light | Direct output |
| 5 | Motor permissives + seal-in circuit | Latch / interlock |
| 6 | Jam detection timer | TON timer |
| 7 | Motor feedback loss check | TON timer |
| 8 | Sensor mismatch detection | Interlock |
| 9 | Fault / alarm light | Output based on fault code |
| 10 | Diverter gate logic | Priority logic |
| 11 | Alarm horn | Multiple condition OR |
| 12 | Part counters (per lane) | CTU counter, rising edge |
| 13 | Production complete cycle | One-shot, setpoint compare |
| 14 | Watchdog heartbeat | Toggle on scan count |

---

## Machine State Machine

```
IDLE ──[START + permissives OK]──► AUTO_RUN
IDLE ──[MODE=Manual]─────────────► MANUAL
AUTO_RUN ──[STOP]────────────────► IDLE
AUTO_RUN ──[E-STOP]──────────────► ESTOP
AUTO_RUN ──[JAM timer done]──────► FAULT (code 1)
AUTO_RUN ──[FB loss > 2s]────────► FAULT (code 2)
MANUAL ──[E-STOP]────────────────► ESTOP
MANUAL ──[STOP / MODE=Auto]──────► IDLE
FAULT ──[RESET + fault clear]────► IDLE
ESTOP ──[E-stop clear + RESET]───► IDLE
```

---

## Modbus Register Map Summary

| Type | Count | Function Code | Notes |
|---|---|---|---|
| Coils | 9 | FC1 | Digital outputs |
| Discrete Inputs | 15 | FC2 | Field sensors + panel inputs |
| Holding Registers | 6 | FC3/FC6 | R/W setpoints (HMI writes) |
| Input Registers | 12 | FC4 | Read-only PLC status |

Full register map: [`docs/register_map.csv`](docs/register_map.csv)

---

## HMI Screens

| Screen | Features |
|---|---|
| **Overview** | State badge, conveyor SVG animation, motor LEDs, box count tiles, speed display |
| **Manual Controls** | Mode toggle, speed slider, gate indicators, fault reset |
| **Alarms** | Active alarm table with ACK, alarm history from SQLite, color-coded priorities |
| **Production Stats** | Box count by type, throughput gauge, OEE-lite %, shift runtime/downtime bars, speed trend chart |
| **Maintenance** | All 15 sensor states, jam timer progress bar, counter values, watchdog heartbeat indicator |
| **Network Status** | Modbus connection, poll latency, topology diagram, protocol reference |

---

## Project Structure

```
LadderLogic/
├── README.md
├── requirements.txt
├── .gitignore
├── start_all.bat
│
├── plc/
│   ├── simulator/
│   │   ├── plc_sim.py          ← Entry point: Modbus TCP server + scan loop
│   │   ├── state_machine.py    ← MachineState enum + transitions
│   │   ├── ladder_routines.py  ← All 14 ladder rungs
│   │   ├── tag_db.py           ← In-memory tag store + register map
│   │   └── io_sim.py           ← Sensor + motor simulation
│   └── ladder_logic/
│       ├── main.st             ← IEC 61131-3 Structured Text (OpenPLC)
│       ├── tag_list.csv
│       └── register_map.csv
│
├── hmi/
│   ├── backend/
│   │   ├── app.py              ← FastAPI + WebSocket server
│   │   ├── modbus_client.py    ← Modbus TCP polling client
│   │   ├── db.py               ← SQLite SCADA historian
│   │   └── models.py           ← Pydantic models
│   └── frontend/
│       ├── index.html          ← 6-tab SPA shell
│       ├── style.css           ← Industrial dark theme
│       ├── app.js              ← WebSocket client + tab router
│       └── screens/
│           ├── overview.js
│           ├── manual.js
│           ├── alarms.js
│           ├── production.js
│           ├── maintenance.js
│           └── network.js
│
├── scada/
│   └── db/
│       └── schema.sql          ← SQLite schema reference
│
└── docs/
    ├── io_list.csv             ← 24 I/O points with wiring notes
    ├── register_map.csv        ← Modbus register assignments
    ├── bom.csv                 ← 25-line Bill of Materials (~$8,100)
    ├── alarm_list.csv          ← 6 alarms with cause/action
    ├── cause_effect_matrix.csv ← Input → output mapping
    ├── controls_narrative.md   ← Sequence of operation
    ├── commissioning_checklist.md ← 40+ check items
    ├── fat_sat_test_sheet.md   ← 8 test sections with pass/fail
    ├── network_diagram.md      ← ASCII topology + production reference
    └── panel_layout.md         ← Panel face, interior, terminal strip
```

---

## Resume Bullets

> Copy and adapt for your resume:

- Built a simulated industrial conveyor sorting cell using PLC ladder logic, HMI/SCADA, and Modbus TCP to demonstrate full-stack controls engineering from I/O to supervisory visualization

- Developed 14-rung IEC 61131-3 ladder logic program for motor control, E-stop interlocks, fault latching, jam detection timers, part counters, diverter gate routing, and watchdog heartbeat using a Python-based virtual PLC

- Implemented Modbus TCP communications between virtual PLC simulator and HMI backend, including a complete register map (9 coils, 15 DI, 6 HR, 12 IR), polling client, and command writes with sub-100ms latency

- Created 6-screen browser HMI with live WebSocket tag streaming, alarm acknowledgment workflow, OEE-lite production metrics, speed trend charting, and SCADA event logging to SQLite

- Produced controls engineering documentation package: I/O list, Bill of Materials, alarm list, cause/effect matrix, commissioning checklist, FAT/SAT test sheet, network topology diagram, and panel layout

---

## Technology Stack

| Component | Technology | Why |
|---|---|---|
| PLC simulator | Python + pymodbus | Real Modbus TCP; no PLC hardware needed |
| HMI backend | FastAPI + uvicorn | Async; WebSocket; production-grade |
| HMI frontend | Vanilla HTML/JS/CSS | No build step; fully portable |
| Database | SQLite + aiosqlite | Zero-config historian; SQL queryable |
| OpenPLC export | IEC 61131-3 ST | Importable into real OpenPLC Runtime |
| Docs | Markdown + CSV | Version-controllable; GitHub-readable |

---

## Adding OpenPLC + Factory I/O (Optional Upgrade)

To run this with actual OpenPLC Runtime and Factory I/O:

1. Install [OpenPLC Runtime](https://autonomylogic.com/docs/openplc-runtime/)
2. Import `plc/ladder_logic/main.st` via the web interface
3. Set Modbus slave address to match register map
4. Connect [Factory I/O](https://factoryio.com/) conveyor scene
5. Map Factory I/O signals to OpenPLC I/O variables
6. Point `hmi/backend/modbus_client.py` to OpenPLC's Modbus address

---

## License

MIT — use freely for portfolio, learning, or project reference.
