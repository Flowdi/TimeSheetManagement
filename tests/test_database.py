import sqlite3
import tempfile
import unittest
from contextlib import closing
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
