"""
HMI Backend — FastAPI application.

Endpoints:
  GET  /              — Serves the HMI frontend (index.html)
  GET  /tags          — Current tag snapshot (JSON)
  POST /command       — Send command to PLC (START/STOP/RESET)
  POST /write         — Write a tag value to PLC holding register
  GET  /alarms        — Active alarms list
  GET  /alarms/history— All alarms
  POST /alarms/ack    — Acknowledge an alarm
  GET  /events        — Event log
  GET  /production    — Production history
  GET  /trend         — Speed trend data
  WS   /ws            — Live tag stream (WebSocket, 500 ms push)

Start: python app.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add backend dir to path
sys.path.insert(0, os.path.dirname(__file__))

import modbus_client as plc
import db as database
from models import CommandRequest, WriteRequest, AlarmAckRequest

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HMI] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hmi")

FRONTEND_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    asyncio.create_task(plc.poll_loop())
    asyncio.create_task(broadcast_loop())
    log.info("=" * 50)
    log.info("  Smart Conveyor HMI Backend")
    log.info("  http://localhost:8000")
    log.info("=" * 50)
    yield


app = FastAPI(title="Smart Conveyor HMI", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# REST API — must be declared BEFORE the static file catch-all mount
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.get("/tags")
async def get_tags():
    tags = dict(plc.live_tags)
    tags["modbus_connected"] = plc.modbus_status["connected"]
    tags["poll_latency_ms"] = plc.modbus_status["poll_latency_ms"]
    tags["server_time"] = datetime.now(timezone.utc).isoformat()
    return JSONResponse(tags)


@app.post("/command")
async def send_command(req: CommandRequest):
    ok = await plc.send_command(req.command)
    cmd_names = {1: "START", 2: "STOP", 3: "RESET", 4: "SHIFT_RESET"}
    name = cmd_names.get(req.command, str(req.command))
    if ok:
        await database.log_event("HMI_COMMAND", f"Operator sent {name}", str(req.command))
    return {"ok": ok, "command": name}


@app.post("/write")
async def write_tag(req: WriteRequest):
    hr_map = {
        "HR_SPEED_SETPOINT": 0,
        "HR_JAM_TIMER_PRESET": 1,
        "HR_MODE_COMMAND": 3,
    }
    if req.tag not in hr_map:
        return JSONResponse({"ok": False, "error": "Tag not writable via this endpoint"}, status_code=400)
    ok = await plc.write_holding_register(hr_map[req.tag], req.value)
    if ok:
        await database.log_event("TAG_WRITE", f"HMI wrote {req.tag}={req.value}")
    return {"ok": ok}


@app.get("/alarms")
async def get_alarms():
    return await database.get_active_alarms()


@app.get("/alarms/history")
async def get_alarm_history():
    return await database.get_alarm_history(200)


@app.post("/alarms/ack")
async def ack_alarm(req: AlarmAckRequest):
    ok = await database.acknowledge_alarm(req.alarm_id)
    if ok:
        await database.log_event("ALARM_ACK", f"Alarm {req.alarm_id} acknowledged")
    return {"ok": ok}


@app.get("/events")
async def get_events():
    return await database.get_events(200)


@app.get("/production")
async def get_production():
    return await database.get_production_history(200)


@app.get("/trend")
async def get_trend():
    return await database.get_speed_trend(120)


# ---------------------------------------------------------------------------
# WebSocket broadcaster
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)
        log.info("WS client connected (%d total)", len(self._clients))

    def disconnect(self, ws: WebSocket):
        self._clients.remove(ws)
        log.info("WS client disconnected (%d total)", len(self._clients))

    async def broadcast(self, data: str):
        dead = []
        for ws in self._clients:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.remove(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; actual data is pushed by broadcast_loop
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

_prev_alarm_word = 0
_prev_state = -1
_trend_tick = 0
_prod_tick = 0


async def broadcast_loop():
    """Push live tags to all WS clients every 500 ms."""
    global _prev_alarm_word, _prev_state, _trend_tick, _prod_tick

    while True:
        await asyncio.sleep(0.5)
        tags = dict(plc.live_tags)
        if not tags:
            continue

        tags["modbus_connected"] = plc.modbus_status["connected"]
        tags["poll_latency_ms"] = plc.modbus_status["poll_latency_ms"]
        tags["server_time"] = datetime.now(timezone.utc).isoformat()

        # Detect new alarms
        alarm_word = tags.get("IR_ALARM_WORD", 0)
        new_bits = alarm_word & ~_prev_alarm_word
        if new_bits:
            for bit in range(4):
                if new_bits & (1 << bit):
                    fault_code = bit + 1
                    await database.log_alarm(fault_code)
                    log.info("Alarm logged: fault code %d", fault_code)
        _prev_alarm_word = alarm_word

        # Detect state changes
        state = tags.get("IR_MACHINE_STATE", -1)
        if state != _prev_state:
            state_names = {0: "IDLE", 1: "AUTO_RUN", 2: "MANUAL", 3: "FAULT", 4: "ESTOP"}
            await database.log_event(
                "STATE_CHANGE",
                f"Machine state: {state_names.get(state, str(state))}",
                str(state),
            )
            _prev_state = state

        # Log speed trend every 10 s (20 half-second ticks)
        _trend_tick += 1
        if _trend_tick >= 20:
            await database.log_speed_trend(tags)
            _trend_tick = 0

        # Log production snapshot every 60 s
        _prod_tick += 1
        if _prod_tick >= 120:
            await database.log_production(tags)
            _prod_tick = 0

        await manager.broadcast(json.dumps(tags))


# ---------------------------------------------------------------------------
# Static file catch-all — MUST be last so REST routes above take priority
# html=True serves index.html for / automatically
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
