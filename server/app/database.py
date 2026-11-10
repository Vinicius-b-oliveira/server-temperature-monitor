import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device        TEXT    NOT NULL,
    received_at   TEXT    NOT NULL,
    uptime_s      INTEGER,
    temp_c        REAL,
    dht_temp_c    REAL,
    humidity_pct  INTEGER,
    lid_open      INTEGER,
    fan_on        INTEGER,
    state         TEXT,
    mode          TEXT,
    warning_c     REAL,
    critical_c    REAL
);

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device        TEXT NOT NULL,
    occurred_at   TEXT NOT NULL,
    kind          TEXT NOT NULL,
    detail        TEXT
);

CREATE INDEX IF NOT EXISTS idx_readings_received_at ON readings (received_at);
"""


def utc_now_iso(delta: timedelta = timedelta(0)) -> str:
    return (datetime.now(timezone.utc) + delta).isoformat(timespec="seconds")


# Uma conexão por operação: o MQTT e a API rodam em threads diferentes
@contextmanager
def _connect(db_path: Path):
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _reading(row: sqlite3.Row) -> dict:
    reading = dict(row)
    reading["lid_open"] = bool(reading["lid_open"])
    reading["fan_on"] = bool(reading["fan_on"])
    return reading


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)


def insert_reading(db_path: Path, reading: dict, received_at: str | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO readings (device, received_at, uptime_s, temp_c, dht_temp_c,"
            " humidity_pct, lid_open, fan_on, state, mode, warning_c, critical_c)"
            " VALUES (:device, :received_at, :uptime_s, :temp_c, :dht_temp_c,"
            " :humidity_pct, :lid_open, :fan_on, :state, :mode, :warning_c, :critical_c)",
            {**reading, "received_at": received_at or utc_now_iso()},
        )


def insert_event(db_path: Path, device: str, kind: str, detail: str | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO events (device, occurred_at, kind, detail) VALUES (?, ?, ?, ?)",
            (device, utc_now_iso(), kind, detail),
        )


def latest_reading(db_path: Path) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
    return _reading(row) if row else None


def readings_since(db_path: Path, minutes: int) -> list[dict]:
    cutoff = utc_now_iso(timedelta(minutes=-minutes))
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM readings WHERE received_at >= ? ORDER BY id", (cutoff,)
        ).fetchall()
    return [_reading(row) for row in rows]


def recent_events(db_path: Path, limit: int) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def last_status(db_path: Path) -> str | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT kind FROM events WHERE kind IN ('online', 'offline') ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return row["kind"] if row else None
