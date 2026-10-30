import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from timesheet.database import Database


class DatabaseBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "source.db")
        with self.db.connect() as connection:
            connection.execute(
                "INSERT INTO audit_log(action,details,created_at) VALUES(?,?,?)",
                ("test", "Sicherungsinhalt", self.db.now()),
            )

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_is_complete_and_independent(self):
        target = self.db.backup(self.root / "backup.db")
        with self.db.connect() as connection:
            connection.execute("DELETE FROM audit_log")
        with closing(sqlite3.connect(target)) as connection:
            self.assertEqual(connection.execute("SELECT details FROM audit_log").fetchone()[0], "Sicherungsinhalt")
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")

    def test_backup_rejects_source_and_existing_file(self):
        with self.assertRaisesRegex(ValueError, "aktive Datenbank"):
            self.db.backup(self.db.path)
        target = self.db.backup(self.root / "backup.db")
        with self.assertRaisesRegex(ValueError, "existiert bereits"):
            self.db.backup(target)

    def test_daily_backup_is_verified_and_idempotent(self):
        backup_day = date(2026, 10, 30)
        target, created = self.db.daily_backup(self.root / "automatic", backup_day)
        repeated_target, repeated_created = self.db.daily_backup(
            self.root / "automatic", backup_day
        )

        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(target, repeated_target)
        self.assertEqual(target.name, "timesheet-auto-20261030.db")
        with closing(sqlite3.connect(target)) as connection:
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")

    def test_database_diagnostics_report_integrity_and_size(self):
        result = self.db.diagnostics()
        self.assertEqual(result["integrity"], "ok")
        self.assertEqual(result["foreign_key_errors"], 0)
        self.assertIn(result["journal_mode"], {"delete", "wal", "memory"})
        self.assertGreater(result["size_bytes"], 0)

    def test_existing_users_receive_default_vacation_allowance(self):
        legacy_path = self.root / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute(
                """CREATE TABLE users (
                    id INTEGER PRIMARY KEY, username TEXT, display_name TEXT,
                    password_hash TEXT, role TEXT, active INTEGER, created_at TEXT
                )"""
            )
            connection.execute(
                "INSERT INTO users VALUES(1,'anna','Anna','hash','employee',1,'2026-01-01')"
            )
            connection.commit()

        migrated = Database(legacy_path)

        with migrated.connect() as connection:
            allowance = connection.execute(
                "SELECT annual_vacation_days FROM users WHERE id=1"
            ).fetchone()[0]
        self.assertEqual(allowance, 30)

    def test_existing_absence_requests_survive_sick_leave_migration(self):
        legacy_path = self.root / "legacy-absence.db"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.executescript("""
                CREATE TABLE users (id INTEGER PRIMARY KEY);
                INSERT INTO users VALUES(1);
                CREATE TABLE absence_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    absence_type TEXT NOT NULL CHECK(absence_type IN ('vacation','holiday','overtime_reduction')),
                    start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    reviewed_by INTEGER REFERENCES users(id), reviewed_at TEXT,
                    created_at TEXT NOT NULL
                );
                INSERT INTO absence_requests
                VALUES(1,1,'vacation','2026-08-01','2026-08-02','Erholung','approved',NULL,NULL,'2026-01-01');
            """)

        migrated = Database(legacy_path)

        with migrated.connect() as connection:
            existing = connection.execute(
                "SELECT absence_type,reason FROM absence_requests WHERE id=1"
            ).fetchone()
            connection.execute(
                """INSERT INTO absence_requests(
                       user_id,absence_type,start_date,end_date,created_at
                   ) VALUES(1,'sick_leave','2026-09-01','2026-09-01','2026-01-01')"""
            )
        self.assertEqual(tuple(existing), ("vacation", "Erholung"))
