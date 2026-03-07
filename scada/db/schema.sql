-- Smart Conveyor Sorting Cell — SCADA SQLite Schema
-- This file is for reference. The database is created automatically by db.py on startup.

CREATE TABLE IF NOT EXISTS alarms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,    -- ISO 8601 UTC timestamp
    alarm_code      INTEGER,          -- 1=JAM 2=FBCK 3=WDG 4=MISMATCH
    description     TEXT,
    priority        TEXT,             -- HIGH / MEDIUM / LOW
    acknowledged    INTEGER DEFAULT 0,
    ack_timestamp   TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    event_type      TEXT,             -- STATE_CHANGE / MODE_CHANGE / HMI_COMMAND / TAG_WRITE / ALARM_ACK
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

-- Useful views for reporting
CREATE VIEW IF NOT EXISTS v_alarm_summary AS
SELECT
    DATE(timestamp) AS shift_date,
    alarm_code,
    description,
    priority,
    COUNT(*) AS occurrences,
    SUM(acknowledged) AS acknowledged_count
FROM alarms
GROUP BY DATE(timestamp), alarm_code;

CREATE VIEW IF NOT EXISTS v_daily_production AS
SELECT
    shift_date,
    MAX(box_total) AS total_boxes,
    MAX(box_small) AS small_boxes,
    MAX(box_large) AS large_boxes,
    MAX(box_metal) AS metal_parts,
    MAX(throughput_per_hr) AS peak_tph
FROM production_counts
GROUP BY shift_date;
