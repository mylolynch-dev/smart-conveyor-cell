# Demo Video

A screen recording of the Smart Conveyor Sorting Cell running will be posted here.

## What the demo shows

1. `start_all.bat` launches both services
2. Browser opens to `http://localhost:8000` — Overview screen
3. Click **START** — conveyor animation activates, state badge turns AUTO_RUN
4. Boxes flow through with color coding by type (green=small, blue=large, amber=metal)
5. Alarm is triggered (jam simulation) — fault banner appears, alarm recorded
6. Alarm acknowledged on Alarms screen
7. FAULT RESET — system returns to IDLE
8. Production Stats screen — box counts, OEE gauge, speed trend chart
9. Maintenance screen — sensor grid, watchdog heartbeat blinking
10. Network Status — Modbus connected, poll latency shown

## Screenshots

See `demo/screenshots/` folder.

Suggested screenshots to capture:
- `overview_running.png` — Conveyor running, AUTO_RUN state
- `overview_fault.png` — Fault banner visible, FAULT state
- `alarms_active.png` — Active alarm table
- `production_stats.png` — OEE gauge and trend chart
- `maintenance_sensors.png` — Sensor state grid
- `network_status.png` — Connection status panel
