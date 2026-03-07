# Control Panel Layout — Smart Conveyor Sorting Cell

**Enclosure:** Hoffman NEMA 12, 36" H × 30" W × 12" D
**Voltage:** 480VAC 3-Phase / 24VDC Control
**Revision:** 1.0

---

## Panel Face Layout

```
┌──────────────────────────────────────────────────────────────────┐
│          SMART CONVEYOR SORTING CELL — CONTROL PANEL             │
│                                                                   │
│   [ESTOP]           ●  ●  ●           [RESET]  [MODE: AUTO/MAN]  │
│   E-STOP            R  A  G           Fault     ┤◄──────────────  │
│   (PULL TO          E  M  R           Reset     Key Switch        │
│    RELEASE)         D  B  N                                       │
│                     E  E  E                                       │
│                     R  R  E                                       │
│                        N                                          │
│                                                                   │
│   [▶ START]                               [■ STOP]               │
│    Green NO                                Red NC                 │
│    22mm                                   22mm                    │
│                                                                   │
│                    [  STACK LIGHT  ]                              │
│                     Red / Amber / Green                           │
│                     Column light                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Panel Interior Layout

```
Top rail (from top, left to right):
  ├── 24VDC PSU (Phoenix Contact — left side)
  ├── PLC chassis (ControlLogix 7-slot — center)
  │     Slot 0: L83E processor
  │     Slot 1: 1756-IB16 DI (card 1)
  │     Slot 2: 1756-IB16 DI (card 2)
  │     Slot 3: 1756-OB16 DO (card 3)
  │     Slots 4-6: spare
  └── Managed Ethernet switch (right side, DIN mount)

Middle rail:
  ├── Motor protection relay (E3 Plus) — left
  ├── Fuse holders F1-F8 — center
  │     F1: 480VAC L1 → VFD (20A)
  │     F2: 480VAC L2 → VFD (20A)
  │     F3: 480VAC L3 → VFD (20A)
  │     F4: 24VDC → DO Card 3 (4A)
  │     F5: 24VDC → Solenoids (2A)
  │     F6: 24VDC → Panel lamps (1A)
  │     F7: 24VDC → Sensors (2A)
  │     F8: Spare
  └── Safety relay module (E-stop circuit) — right

Bottom rail:
  ├── Terminal blocks XT1-XT60 (Phoenix PT 2.5)
  │     XT1-XT15: Digital inputs from field
  │     XT16-XT25: Digital outputs to field
  │     XT26-XT35: 24VDC power distribution
  │     XT36-XT45: 480VAC distribution
  │     XT46-XT60: Spare / signal grounds
  └── Grounding bar

Cable entry: Bottom of enclosure, IP68 cable glands
```

## Terminal Strip — XT1 to XT15 (Digital Inputs)

| Terminal | Wire # | Description | I/O Tag |
|---|---|---|---|
| XT1 | W001 | Start pushbutton + (24VDC) | IN_START_PB |
| XT2 | W002 | Stop pushbutton + (24VDC) | IN_STOP_PB |
| XT3 | W003 | E-stop NC contact A1 | IN_ESTOP |
| XT4 | W004 | E-stop NC contact A2 | IN_ESTOP (return) |
| XT5 | W005 | Fault reset pushbutton | IN_FAULT_RESET |
| XT6 | W006 | Mode selector switch | IN_MODE_SELECT |
| XT7 | W007 | Motor aux contact | IN_MOTOR_FEEDBACK |
| XT8 | W008 | Jam sensor signal | IN_JAM_SENSOR |
| XT9 | W009 | Entry photoelectric signal | IN_BOX_DETECT |
| XT10 | W010 | Size sensor small output | IN_SIZE_SMALL |
| XT11 | W011 | Size sensor large output | IN_SIZE_LARGE |
| XT12 | W012 | Metal detector output | IN_METAL_DETECT |
| XT13 | W013 | Color sensor red | IN_COLOR_RED |
| XT14 | W014 | Color sensor blue | IN_COLOR_BLUE |
| XT15 | W015 | Gate A confirm limit | IN_GATE_A_CONFIRM |

## Terminal Strip — XT16 to XT25 (Digital Outputs)

| Terminal | Wire # | Description | I/O Tag |
|---|---|---|---|
| XT16 | W016 | Motor starter coil | OUT_MOTOR_RUN |
| XT17 | W017 | Gate A solenoid | OUT_GATE_A |
| XT18 | W018 | Gate B solenoid | OUT_GATE_B |
| XT19 | W019 | Gate C solenoid | OUT_GATE_C |
| XT20 | W020 | Alarm horn | OUT_ALARM_HORN |
| XT21 | W021 | E-stop pilot light (red) | OUT_ESTOP_LIGHT |
| XT22 | W022 | Fault pilot light (amber) | OUT_FAULT_LIGHT |
| XT23 | W023 | Run pilot light (green) | OUT_RUN_LIGHT |
| XT24 | W024 | Stack light red | — |
| XT25 | W025 | Stack light green | — |

---

## Wire Color Code

| Color | Usage |
|---|---|
| Red | 24VDC positive / L1 |
| Black | 24VDC negative / L2 |
| Green/Yellow | Safety ground |
| Blue | Neutral (where applicable) |
| White | Signal / field device wiring |
| Orange | Interposing relay outputs |

---

## AutoCAD Drawing Index

| Drawing # | Title | Sheet |
|---|---|---|
| SCC-E-001 | One-line diagram — 480VAC power distribution | 1 |
| SCC-E-002 | Control schematic — 24VDC I/O | 2 |
| SCC-E-003 | E-stop safety circuit | 3 |
| SCC-E-004 | Terminal strip layout XT1-XT60 | 4 |
| SCC-E-005 | Panel face layout | 5 |
| SCC-E-006 | Panel interior layout | 6 |
| SCC-E-007 | I/O card wiring — DI card 1 | 7 |
| SCC-E-008 | I/O card wiring — DI card 2 / DO card 3 | 8 |
| SCC-E-009 | Network topology diagram | 9 |

*Note: For this portfolio project, drawing SCC-E-009 (network topology) is provided as ASCII art in network_diagram.md. AutoCAD drawings SCC-E-001 through SCC-E-008 represent the deliverables that would be produced during a real project.*
