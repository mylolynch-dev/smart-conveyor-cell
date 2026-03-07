# Network Architecture Diagram — Smart Conveyor Sorting Cell

## ASCII Network Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OPERATOR LEVEL                               │
│                                                                     │
│  ┌───────────────────────────────┐                                  │
│  │     Operator Workstation       │                                 │
│  │  OS: Windows 10/11             │                                 │
│  │  Browser: Chrome/Firefox/Edge  │                                 │
│  │  URL: http://localhost:8000    │                                 │
│  │                                │                                 │
│  │  HMI Frontend (HTML/JS)        │                                 │
│  │  ├── WebSocket /ws (live tags) │                                 │
│  │  └── REST API (commands/data)  │                                 │
│  └───────────────┬───────────────┘                                 │
│                  │ HTTP / WebSocket                                  │
│                  │ localhost port 8000                               │
└──────────────────┼──────────────────────────────────────────────────┘
                   │
┌──────────────────┼──────────────────────────────────────────────────┐
│                  │   CONTROL LEVEL (same machine, dev env)           │
│  ┌───────────────▼───────────────┐                                  │
│  │     HMI Backend               │                                  │
│  │  FastAPI + Uvicorn             │                                  │
│  │  Port: 8000                    │                                  │
│  │                                │                                  │
│  │  Tasks:                        │                                  │
│  │  ├── Poll Modbus every 500ms   │                                  │
│  │  ├── Push tags via WebSocket   │                                  │
│  │  ├── Write commands to PLC     │                                  │
│  │  └── Log to SQLite historian   │                                  │
│  └───────────────┬───────────────┘                                  │
│                  │                          ┌──────────────────────┐ │
│                  │ Modbus TCP               │ SQLite Database       │ │
│                  │ port 5020                │ scada/db/conveyor.db │ │
│  ┌───────────────▼───────────────┐         │ Tables:               │ │
│  │     PLC Simulator             │         │  - alarms             │ │
│  │  Python / pymodbus            │         │  - events             │ │
│  │  Port: 5020                   ├────────►│  - production_counts  │ │
│  │                               │         │  - speed_trend        │ │
│  │  Registers:                   │         │  - shift_summary      │ │
│  │  ├── Coils (9 outputs)        │         └──────────────────────┘ │
│  │  ├── DI (15 inputs)           │                                   │
│  │  ├── HR (6 setpoints)         │                                   │
│  │  └── IR (12 status regs)      │                                   │
│  │                               │                                   │
│  │  Scan Loop (100ms):           │                                   │
│  │  ├── I/O Simulator            │                                   │
│  │  ├── Ladder Routines (14 rngs)│                                   │
│  │  └── State Machine            │                                   │
│  └───────────────────────────────┘                                   │
└──────────────────────────────────────────────────────────────────────┘
```

## Production Plant Topology (Real Implementation Reference)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ENTERPRISE LEVEL (MES/ERP)                        │
│  ┌────────────────────────┐   ┌─────────────────────────┐           │
│  │   ERP System            │   │  MES / Production DB     │          │
│  │  (SAP / Oracle)         │   │  (SQL Server / Oracle)   │          │
│  └───────────┬────────────┘   └─────────────┬───────────┘           │
└──────────────┼──────────────────────────────┼────────────────────────┘
               │ OPC-UA / REST                 │ JDBC / ODBC
┌──────────────┼──────────────────────────────┼────────────────────────┐
│              │    SUPERVISORY LEVEL          │                         │
│  ┌───────────▼──────────────────────────────▼───────────┐            │
│  │   SCADA Server (Ignition / Wonderware)                │            │
│  │   ├── OPC-UA Server (tags from all PLCs)              │            │
│  │   ├── Historian (tag logging)                         │            │
│  │   ├── Alarm server                                    │            │
│  │   └── Report generation                               │            │
│  └───────────────────────────────┬───────────────────────┘            │
│                                  │ Ethernet / OPC-UA                  │
│  ┌───────────────────────────────┼───────────────────────────────┐   │
│  │   Plant Network (Industrial Ethernet — managed switches)       │   │
│  │                               │                               │   │
│  │  ┌──────────────────┐  ┌──────▼──────────────────┐           │   │
│  │  │  Operator Panel   │  │   HMI Station           │           │   │
│  │  │  (Panelview+)     │  │   (Ignition Client)     │           │   │
│  │  └──────────────────┘  └─────────────────────────┘           │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
               │ EtherNet/IP (Allen-Bradley)
               │ or PROFINET (Siemens)
┌──────────────┼──────────────────────────────────────────────────────┐
│              │    CONTROL LEVEL                                       │
│  ┌───────────▼───────────┐  ┌──────────────────────┐                │
│  │  PLC (ControlLogix)   │  │  Safety PLC (GuardLogix)│             │
│  │  L83E                 │  │  E-stop / safety circuit│             │
│  └──────────┬────────────┘  └──────────────────────┘                │
└─────────────┼────────────────────────────────────────────────────────┘
              │ DeviceNet / IO-Link / point-to-point 24VDC wiring
┌─────────────┼────────────────────────────────────────────────────────┐
│             │    FIELD LEVEL                                          │
│  ┌──────────▼──────────────────────────────────────────────────────┐ │
│  │  Field Devices                                                   │ │
│  │  ├── Photoelectric sensors (24VDC PNP)                          │ │
│  │  ├── Inductive proximity sensors                                 │ │
│  │  ├── Color / size sensors                                        │ │
│  │  ├── Motor starter / VFD                                         │ │
│  │  ├── Pneumatic solenoid valves                                   │ │
│  │  └── Panel pushbuttons / selector switches / pilot lights        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

## Protocol Summary

| Layer | Protocol | Standard | Notes |
|---|---|---|---|
| Simulation (this project) | Modbus TCP | IEC 60870 | PLC sim ↔ HMI backend |
| Allen-Bradley real plant | EtherNet/IP | ODVA | CIP over Ethernet; implicit + explicit messaging |
| Siemens real plant | PROFINET | IEC 61158 | RT and IRT classes; PLC to HMI/drives |
| Smart sensors | IO-Link | IEC 61131-9 | Point-to-point below fieldbus; sensor parameterization |
| Legacy / simple devices | DeviceNet | ODVA | CAN-based; being superseded by EtherNet/IP |
| SCADA ↔ PLC | OPC-UA | IEC 62541 | Vendor-neutral; recommended for new installations |
