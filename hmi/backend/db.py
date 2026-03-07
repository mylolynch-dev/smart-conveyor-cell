"""
SQLite database interface for SCADA historian data.

Tables:
  alarms          — alarm events with acknowledgement tracking
  events          — general state change / operator action log
  production_counts — periodic production snapshots
  speed_trend     — speed and state samples for trending
  shift_summary   — end-of-shift summary records
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

import aiosqlite

log = logging.getLogger("db")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scada", "db", "conveyor.db")
DB_PATH = os.path.normpath(DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS alarms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    alarm_code      INTEGER,
    description     TEXT,
    priority        TEXT,
    acknowledged    INTEGER DEFAULT 0,
    ack_timestamp   TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    event_type      TEXT,
    description     TEXT,
    value           TEXT
);

CREATE TABLE IF NOT EXISTS production_counts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    shift_date      TEXT,
    box_total       INTEGER,
    box_small       INTEGER,
    box_large       INTEGER,
    box_metal       INTEGER,
    throughput_per_hr REAL
);

CREATE TABLE IF NOT EXISTS speed_trend (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    speed_setpoint  INTEGER,
    speed_actual    INTEGER,
    machine_state   INTEGER
);

CREATE TABLE IF NOT EXISTS shift_summary (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_date      TEXT,
    start_time      TEXT,
    end_time        TEXT,
    runtime_secs    INTEGER,
    downtime_secs   INTEGER,
    total_boxes     INTEGER,
    oee_pct         REAL
);
"""

ALARM_DESCRIPTIONS = {
    1: ("Conveyor jam detected", "HIGH"),
    2: ("Motor run feedback lost", "HIGH"),
    3: ("Watchdog / communications loss", "MEDIUM"),
    4: ("Size sensor mismatch", "MEDIUM"),
}


async def init_db() -> None:
    """Create database and tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()
    log.info("Database ready: %s", DB_PATH)


async def log_alarm(alarm_code: int) -> int:
    """Insert a new alarm record. Returns the new alarm ID."""
    ts = datetime.now(timezone.utc).isoformat()
    desc, priority = ALARM_DESCRIPTIONS.get(alarm_code, (f"Alarm {alarm_code}", "LOW"))
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "INSERT INTO alarms (timestamp, alarm_code, description, priority) VALUES (?,?,?,?)",
            (ts, alarm_code, desc, priority),
        )
        await conn.commit()
        return cursor.lastrowid


async def acknowledge_alarm(alarm_id: int) -> bool:
    ts = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE alarms SET acknowledged=1, ack_timestamp=? WHERE id=?",
            (ts, alarm_id),
        )
        await conn.commit()
    return True


async def get_active_alarms() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM alarms WHERE acknowledged=0 ORDER BY timestamp DESC LIMIT 50"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_alarm_history(limit: int = 100) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM alarms ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def log_event(event_type: str, description: str, value: str = "") -> None:
    ts = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO events (timestamp, event_type, description, value) VALUES (?,?,?,?)",
            (ts, event_type, description, value),
        )
        await conn.commit()


async def get_events(limit: int = 100) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def log_production(tags: dict) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    shift_date = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO production_counts
               (timestamp, shift_date, box_total, box_small, box_large, box_metal, throughput_per_hr)
               VALUES (?,?,?,?,?,?,?)""",
            (
                ts, shift_date,
                tags.get("IR_BOX_COUNT_TOTAL", 0),
                tags.get("IR_BOX_COUNT_SMALL", 0),
                tags.get("IR_BOX_COUNT_LARGE", 0),
                tags.get("IR_BOX_COUNT_METAL", 0),
                tags.get("IR_THROUGHPUT_PER_HR", 0),
            ),
        )
        await conn.commit()


async def get_production_history(limit: int = 100) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM production_counts ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def log_speed_trend(tags: dict) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO speed_trend (timestamp, speed_setpoint, speed_actual, machine_state) VALUES (?,?,?,?)",
            (
                ts,
                tags.get("HR_SPEED_SETPOINT", 0),
                tags.get("IR_SPEED_ACTUAL", 0),
                tags.get("IR_MACHINE_STATE", 0),
            ),
        )
        await conn.commit()


async def get_speed_trend(limit: int = 120) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM speed_trend ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in reversed(rows)]  # oldest first for charting
