from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from datetime import date, datetime
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
    annual_vacation_days INTEGER NOT NULL DEFAULT 30 CHECK(annual_vacation_days BETWEEN 0 AND 365),
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
    absence_type TEXT NOT NULL CHECK(absence_type IN ('vacation','holiday','overtime_reduction','sick_leave')),
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
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    work_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','failed','synced')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    next_attempt_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, work_date)
);
CREATE INDEX IF NOT EXISTS idx_sync_queue_due ON sync_queue(status, next_attempt_at);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            user_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(users)")
            }
            if "annual_vacation_days" not in user_columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN annual_vacation_days INTEGER NOT NULL DEFAULT 30"
                )
            absence_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='absence_requests'"
            ).fetchone()["sql"]
            if "sick_leave" not in absence_schema:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.executescript("""
                    CREATE TABLE absence_requests_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        absence_type TEXT NOT NULL CHECK(absence_type IN ('vacation','holiday','overtime_reduction','sick_leave')),
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        reason TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
                        reviewed_by INTEGER REFERENCES users(id),
                        reviewed_at TEXT,
                        created_at TEXT NOT NULL
                    );
                    INSERT INTO absence_requests_new
                    SELECT * FROM absence_requests;
                    DROP TABLE absence_requests;
                    ALTER TABLE absence_requests_new RENAME TO absence_requests;
                """)
                connection.execute("PRAGMA foreign_keys = ON")
            now = self.now()
            connection.execute(
                """INSERT OR IGNORE INTO sync_queue(
                       user_id,work_date,status,attempts,last_error,next_attempt_at,updated_at
                   )
                   SELECT DISTINCT user_id,substr(occurred_at,1,10),'pending',0,'',?,?
                   FROM time_events""",
                (now, now),
            )

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

    def backup(self, destination: Path | str) -> Path:
        target = Path(destination).resolve()
        if target == self.path.resolve():
            raise ValueError("Die Sicherung darf nicht die aktive Datenbank ersetzen.")
        if target.exists():
            raise ValueError("Die Sicherungsdatei existiert bereits. Bitte einen neuen Namen wählen.")
        # Exclusive creation also prevents a file created concurrently from being overwritten.
        with target.open("xb"):
            pass
        with self.connect() as source:
            with closing(sqlite3.connect(target)) as backup_connection:
                source.backup(backup_connection)
                result = backup_connection.execute("PRAGMA quick_check").fetchone()[0]
                if result != "ok":
                    raise ValueError("Die Datenbanksicherung hat die Integritätsprüfung nicht bestanden.")
        return target

    def daily_backup(self, directory: Path | str, backup_date: date | None = None):
        """Create at most one verified automatic backup for a calendar day."""
        backup_date = backup_date or date.today()
        backup_directory = Path(directory)
        backup_directory.mkdir(parents=True, exist_ok=True)
        target = backup_directory / f"timesheet-auto-{backup_date:%Y%m%d}.db"
        if target.exists():
            with closing(sqlite3.connect(target)) as connection:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Die vorhandene automatische Sicherung ist beschädigt.")
            return target, False
        return self.backup(target), True

    @staticmethod
    def prune_daily_backups(directory: Path | str, retain: int = 14):
        try:
            retain = int(retain)
        except (TypeError, ValueError) as error:
            raise ValueError("Die Aufbewahrungsanzahl muss eine ganze Zahl sein.") from error
        if not 1 <= retain <= 3650:
            raise ValueError("Es müssen zwischen 1 und 3650 Sicherungen aufbewahrt werden.")
        candidates = []
        for path in Path(directory).glob("timesheet-auto-*.db"):
            try:
                backup_date = datetime.strptime(path.stem.removeprefix("timesheet-auto-"), "%Y%m%d")
            except ValueError:
                continue
            candidates.append((backup_date, path))
        candidates.sort(reverse=True)
        removed = []
        for _, path in candidates[retain:]:
            path.unlink()
            removed.append(path)
        return removed

    def diagnostics(self) -> dict:
        with self.connect() as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        return {
            "integrity": integrity,
            "foreign_key_errors": foreign_key_errors,
            "journal_mode": journal_mode,
            "size_bytes": self.path.stat().st_size,
        }

    def scalar(self, sql: str, parameters=()):
        with self.connect() as connection:
            row = connection.execute(sql, parameters).fetchone()
            return row[0] if row else None

    def rows(self, sql: str, parameters=()):
        with self.connect() as connection:
            return connection.execute(sql, parameters).fetchall()
