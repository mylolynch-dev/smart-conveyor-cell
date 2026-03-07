"""
PLC Simulator — Main entry point.

Runs the Modbus TCP server (port 5020) and executes the scan loop at 100 ms intervals.
Port 5020 is used instead of the standard 502 to avoid requiring admin/root privileges.

Architecture:
  1. pymodbus AsyncModbusTcpServer runs in the background
  2. A separate thread executes the scan loop every 100 ms
  3. After each scan, the Modbus datastore is updated to reflect current tag values
  4. HMI writes to holding registers are pulled into TagDB before each scan

Start: python plc_sim.py
"""

import sys
import os
import time
import logging
import threading
import asyncio

# Add this directory to path so imports work from any cwd
sys.path.insert(0, os.path.dirname(__file__))

from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.device import ModbusDeviceIdentification

from tag_db import TagDB
from state_machine import StateMachine, FaultCode
from ladder_routines import LadderRoutines
from io_sim import IOSimulator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PLC-SIM] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("plc_sim")

MODBUS_HOST = "0.0.0.0"
MODBUS_PORT = 5020
SCAN_INTERVAL = 0.1   # 100 ms scan cycle

# ---------------------------------------------------------------------------
# Build Modbus datastore
# ---------------------------------------------------------------------------

def build_datastore():
    """Create a Modbus slave context with 32 slots per register type."""
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [False] * 32),    # discrete inputs
        co=ModbusSequentialDataBlock(0, [False] * 32),    # coils
        hr=ModbusSequentialDataBlock(0, [0] * 32),        # holding registers
        ir=ModbusSequentialDataBlock(0, [0] * 32),        # input registers
    )
    return ModbusServerContext(slaves=store, single=True)


# ---------------------------------------------------------------------------
# Sync TagDB → Modbus datastore
# ---------------------------------------------------------------------------

def push_to_modbus(context: ModbusServerContext, db: TagDB) -> None:
    """Write current tag values into the Modbus datastore after each scan."""
    store = context[0]

    coils = db.coils_list()
    store.setValues(1, 0, coils)       # FC1: coils

    di = db.di_list()
    store.setValues(2, 0, di)          # FC2: discrete inputs

    ir = db.ir_list()
    store.setValues(4, 0, ir)          # FC4: input registers


def pull_from_modbus(context: ModbusServerContext, db: TagDB) -> None:
    """Read HMI-written holding registers from Modbus datastore into TagDB."""
    store = context[0]
    hr_values = store.getValues(3, 0, count=16)   # FC3: holding registers
    db.apply_hr_from_modbus(hr_values)


# ---------------------------------------------------------------------------
# Scan loop (runs in a background thread)
# ---------------------------------------------------------------------------

def scan_loop(context: ModbusServerContext, db: TagDB, sm: StateMachine,
              ladder: LadderRoutines, io_sim: IOSimulator) -> None:
    """100 ms scan cycle: pull HMI writes → simulate I/O → run ladder → push to Modbus."""
    log.info("Scan loop started (%.0f ms cycle)", SCAN_INTERVAL * 1000)
    prev_state = sm.state
    scan_num = 0

    while True:
        t0 = time.time()
        scan_num += 1

        try:
            # 1. Pull any HMI writes from Modbus HR registers
            pull_from_modbus(context, db)

            # 2. Simulate physical I/O (sensors, motor feedback)
            io_sim.tick(
                motor_running=db.get("OUT_MOTOR_RUN"),
                machine_state_val=int(sm.state),
            )

            # 3. Execute all ladder logic rungs (state machine transition
            #    is called inside ladder.execute() after HMI command processing)
            ladder.execute()

            # 4. Push tag values back to Modbus datastore
            push_to_modbus(context, db)

            # Log state changes
            if sm.state != prev_state:
                log.info("State: %s → %s  (fault=%s)",
                         prev_state.name, sm.state.name, sm.fault_code.name)
                prev_state = sm.state

            # Log throughput every 60 scans (6 s)
            if scan_num % 60 == 0:
                snap = db.snapshot()
                log.info(
                    "Scan #%d | State: %-10s | Boxes: %d | Speed: %d%% | TPH: %d",
                    scan_num,
                    sm.state.name,
                    snap["IR_BOX_COUNT_TOTAL"],
                    snap["IR_SPEED_ACTUAL"],
                    snap["IR_THROUGHPUT_PER_HR"],
                )

        except Exception as exc:
            log.error("Scan error: %s", exc, exc_info=True)

        # Maintain precise scan interval
        elapsed = time.time() - t0
        sleep_time = max(0.0, SCAN_INTERVAL - elapsed)
        time.sleep(sleep_time)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    db = TagDB()
    sm = StateMachine()
    ladder = LadderRoutines(db, sm)
    io_sim = IOSimulator(db)

    context = build_datastore()

    # Start scan loop in a daemon thread
    t = threading.Thread(
        target=scan_loop,
        args=(context, db, sm, ladder, io_sim),
        daemon=True,
        name="ScanLoop",
    )
    t.start()

    # Device identification (optional — shows up in Modbus discovery)
    identity = ModbusDeviceIdentification()
    identity.VendorName = "SmartConveyor"
    identity.ProductCode = "SCC-1"
    identity.VendorUrl = "https://github.com"
    identity.ProductName = "Smart Conveyor Sorting Cell PLC Simulator"
    identity.ModelName = "VirtualPLC"
    identity.MajorMinorRevision = "1.0"

    log.info("=" * 55)
    log.info("  Smart Conveyor Sorting Cell — PLC Simulator")
    log.info("  Modbus TCP server: %s:%d", MODBUS_HOST, MODBUS_PORT)
    log.info("  Scan cycle: %.0f ms", SCAN_INTERVAL * 1000)
    log.info("=" * 55)
    log.info("HMI Command register (HR[4]): 1=START 2=STOP 3=RESET 4=SHIFT_RESET")
    log.info("Press Ctrl+C to stop.")

    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=(MODBUS_HOST, MODBUS_PORT),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("PLC simulator stopped.")
