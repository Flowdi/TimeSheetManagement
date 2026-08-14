from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('employee', 'admin')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS time_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL CHECK(event_type IN ('work_start','break_start','break_end','work_end')),
    occurred_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'app',
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_user_time ON time_events(user_id, occurred_at);
CREATE TABLE IF NOT EXISTS absence_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    absence_type TEXT NOT NULL CHECK(absence_type IN ('vacation','holiday','overtime_reduction')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS correction_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    work_date TEXT NOT NULL,
    proposed_start TEXT NOT NULL,
    proposed_end TEXT NOT NULL,
    proposed_break_minutes INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def scalar(self, sql: str, parameters=()):
        with self.connect() as connection:
            row = connection.execute(sql, parameters).fetchone()
            return row[0] if row else None

    def rows(self, sql: str, parameters=()):
        with self.connect() as connection:
            return connection.execute(sql, parameters).fetchall()

