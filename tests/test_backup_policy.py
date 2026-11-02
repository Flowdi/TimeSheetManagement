from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from timesheet.backup_policy import BackupPolicy, run_backup_policy
from timesheet.database import Database


class BackupPolicyTests(unittest.TestCase):
    def test_defaults_enable_daily_backups_for_fourteen_files(self):
        policy = BackupPolicy.from_settings({}, Path("default-backups"))
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.directory, Path("default-backups"))
        self.assertEqual(policy.retention_count, 14)

    def test_saved_backup_settings_are_loaded(self):
        policy = BackupPolicy.from_settings(
            {
                "automatic_backup_enabled": False,
                "automatic_backup_directory": "D:/Sicherungen/Zeiterfassung",
                "automatic_backup_retention": "30",
            },
            Path("default-backups"),
        )
        self.assertFalse(policy.enabled)
        self.assertEqual(policy.directory, Path("D:/Sicherungen/Zeiterfassung"))
        self.assertEqual(policy.retention_count, 30)

    def test_invalid_settings_fall_back_to_safe_defaults(self):
        policy = BackupPolicy.from_settings(
            {
                "automatic_backup_enabled": "yes",
                "automatic_backup_directory": 123,
                "automatic_backup_retention": 0,
            },
            Path("default-backups"),
        )
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.directory, Path("default-backups"))
        self.assertEqual(policy.retention_count, 14)

    def test_running_policy_creates_backup_and_reports_repeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = Database(root / "timesheet.db")
            policy = BackupPolicy(True, root / "backups", 14)

            first = run_backup_policy(database, policy)
            second = run_backup_policy(database, policy)

            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["target"], second["target"])

    def test_disabled_policy_does_not_create_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_backup_policy(
                Database(root / "timesheet.db"),
                BackupPolicy(False, root / "backups", 14),
            )
            self.assertFalse(result["enabled"])
            self.assertFalse((root / "backups").exists())


if __name__ == "__main__":
    unittest.main()
