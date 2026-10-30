from __future__ import annotations

import unittest
from pathlib import Path

from timesheet.backup_policy import BackupPolicy


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


if __name__ == "__main__":
    unittest.main()
