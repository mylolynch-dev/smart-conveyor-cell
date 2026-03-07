"""
Modbus TCP client — polls the PLC simulator and pushes writes.

Uses pymodbus AsyncModbusTcpClient.
Runs as a background asyncio task; publishes snapshots to a shared dict.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

log = logging.getLogger("modbus_client")

PLC_HOST = "127.0.0.1"
PLC_PORT = 5020
POLL_INTERVAL = 0.5   # seconds

# Shared state — written by poll loop, read by WebSocket broadcaster
live_tags: dict = {}
modbus_status: dict = {
    "connected": False,
    "last_ok": None,
    "poll_latency_ms": 0.0,
    "error_count": 0,
}


async def poll_loop() -> None:
    """Continuously polls PLC Modbus registers and updates live_tags."""
    global live_tags, modbus_status

    client = AsyncModbusTcpClient(PLC_HOST, port=PLC_PORT)

    log.info("Modbus client connecting to %s:%d", PLC_HOST, PLC_PORT)

    while True:
        try:
            if not client.connected:
                await client.connect()
                if client.connected:
                    log.info("Modbus TCP connected to PLC simulator")

            if client.connected:
                t0 = time.monotonic()
                tags = await _read_all(client)
                latency = (time.monotonic() - t0) * 1000

                live_tags.update(tags)
                modbus_status["connected"] = True
                modbus_status["last_ok"] = datetime.now(timezone.utc).isoformat()
                modbus_status["poll_latency_ms"] = round(latency, 1)
            else:
                modbus_status["connected"] = False

        except (ModbusException, ConnectionRefusedError, OSError) as exc:
            modbus_status["connected"] = False
            modbus_status["error_count"] += 1
            log.warning("Modbus poll error: %s", exc)
            await asyncio.sleep(2)

        await asyncio.sleep(POLL_INTERVAL)


async def _read_all(client: AsyncModbusTcpClient) -> dict:
    """Read all register banks and return a flat tag dict."""
    tags = {}

    # Read coils (FC1) — addresses 0–15
    r = await client.read_coils(0, count=16, slave=1)
    if not r.isError():
        bits = r.bits[:16]
        coil_names = [
            "OUT_MOTOR_RUN", "OUT_GATE_A", "OUT_GATE_B", "OUT_GATE_C",
            "OUT_ALARM_HORN", "OUT_ESTOP_LIGHT", "OUT_FAULT_LIGHT",
            "OUT_RUN_LIGHT", "OUT_HEARTBEAT",
        ]
        for i, name in enumerate(coil_names):
            tags[name] = bool(bits[i]) if i < len(bits) else False

    # Read discrete inputs (FC2) — addresses 0–15
    r = await client.read_discrete_inputs(0, count=16, slave=1)
    if not r.isError():
        bits = r.bits[:16]
        di_names = [
            "IN_START_PB", "IN_STOP_PB", "IN_ESTOP", "IN_FAULT_RESET",
            "IN_MODE_SELECT", "IN_MOTOR_FEEDBACK", "IN_JAM_SENSOR",
            "IN_BOX_DETECT", "IN_SIZE_SMALL", "IN_SIZE_LARGE",
            "IN_METAL_DETECT", "IN_COLOR_RED", "IN_COLOR_BLUE",
            "IN_GATE_A_CONFIRM", "IN_GATE_B_CONFIRM",
        ]
        for i, name in enumerate(di_names):
            tags[name] = bool(bits[i]) if i < len(bits) else False

    # Read holding registers (FC3) — addresses 0–15
    r = await client.read_holding_registers(0, count=16, slave=1)
    if not r.isError():
        regs = r.registers
        hr_names = [
            "HR_SPEED_SETPOINT", "HR_JAM_TIMER_PRESET", "HR_FAULT_CODE",
            "HR_MODE_COMMAND", "HR_HMI_COMMAND", "HR_SHIFT_RESET",
        ]
        for i, name in enumerate(hr_names):
            tags[name] = int(regs[i]) if i < len(regs) else 0

    # Read input registers (FC4) — addresses 0–15
    r = await client.read_input_registers(0, count=16, slave=1)
    if not r.isError():
        regs = r.registers
        ir_names = [
            "IR_BOX_COUNT_TOTAL", "IR_BOX_COUNT_SMALL", "IR_BOX_COUNT_LARGE",
            "IR_BOX_COUNT_METAL", "IR_SPEED_ACTUAL", "IR_MACHINE_STATE",
            "IR_RUNTIME_SECS", "IR_DOWNTIME_SECS", "IR_THROUGHPUT_PER_HR",
            "IR_JAM_TIMER_ACC", "IR_ALARM_WORD", "IR_LAST_FAULT_CODE",
        ]
        for i, name in enumerate(ir_names):
            tags[name] = int(regs[i]) if i < len(regs) else 0

    return tags


async def write_holding_register(address: int, value: int) -> bool:
    """Write a single holding register value to the PLC."""
    client = AsyncModbusTcpClient(PLC_HOST, port=PLC_PORT)
    try:
        await client.connect()
        result = await client.write_register(address, value, slave=1)
        client.close()
        return not result.isError()
    except Exception as exc:
        log.error("Modbus write error (HR[%d]=%d): %s", address, value, exc)
        return False


async def send_command(cmd_value: int) -> bool:
    """Write command value to HR[4] (HMI command register)."""
    return await write_holding_register(4, cmd_value)


async def set_speed(speed_pct: int) -> bool:
    """Write speed setpoint to HR[0]."""
    return await write_holding_register(0, max(0, min(100, speed_pct)))


async def set_mode(mode: int) -> bool:
    """Write mode (0=Auto, 1=Manual) to HR[3]."""
    return await write_holding_register(3, mode)
