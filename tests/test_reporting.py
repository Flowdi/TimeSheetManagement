from __future__ import annotations

import csv
import io
import unittest

from timesheet.reporting import (
    REPORT_HEADERS,
    audit_entries_csv,
    monthly_report_csv,
    system_diagnostics_text,
)


class ReportingTests(unittest.TestCase):
    def test_monthly_report_csv_contains_all_report_columns(self):
        content = monthly_report_csv(
            [
                {
                    "display_name": "Jörg Müller",
                    "work_minutes": 480,
                    "scheduled_days": 21,
                    "target_minutes": 7680,
                    "monthly_balance_minutes": -7200,
                    "overtime_minutes": -30,
                    "absence_days": 3,
                    "vacation_days": 1,
                    "holiday_days": 1,
                    "overtime_reduction_days": 1,
                    "rest_violation_days": 1,
                    "warning_days": 2,
                }
            ],
            2026,
            8,
        )
        rows = list(csv.reader(io.StringIO(content), delimiter=";"))
        self.assertEqual(tuple(rows[0]), REPORT_HEADERS)
        self.assertEqual(
            rows[1],
            ["2026-08", "Jörg Müller", "08:00 h", "21", "128:00 h", "-120:00 h", "-00:30 h", "3", "1", "1", "1", "1", "2"],
        )

    def test_monthly_report_csv_can_export_empty_report(self):
        content = monthly_report_csv([], 2026, 8)
        rows = list(csv.reader(io.StringIO(content), delimiter=";"))
        self.assertEqual(rows, [list(REPORT_HEADERS)])

    def test_audit_csv_uses_readable_action_label(self):
        content = audit_entries_csv([{
            "created_at": "2026-09-25T10:30:00+02:00", "actor_name": "Admin",
            "action": "password_reset", "action_label": "Passwort zurückgesetzt",
            "details": "Passwort für Anna zurückgesetzt",
        }])
        rows = list(csv.reader(io.StringIO(content), delimiter=";"))
        self.assertEqual(rows[0], ["Zeitpunkt", "Akteur", "Aktion", "Details"])
        self.assertEqual(rows[1][2], "Passwort zurückgesetzt")

    def test_system_diagnostics_text_formats_health_summary(self):
        content = system_diagnostics_text({
            "integrity": "ok",
            "foreign_key_errors": 0,
            "journal_mode": "wal",
            "size_bytes": 1536,
            "active_users": 3,
            "total_users": 4,
            "time_events": 42,
            "pending_absences": 2,
            "pending_corrections": 1,
            "sync": {"pending": 1, "failed": 2, "synced": 39},
        })

        self.assertIn("Datenbankintegrität: OK", content)
        self.assertIn("Datenbankgröße: 1.5 KiB", content)
        self.assertIn("Benutzer: 3 aktiv / 4 gesamt", content)
        self.assertIn("Google-Sync: 1 offen, 2 fehlgeschlagen, 39 synchronisiert", content)


if __name__ == "__main__":
    unittest.main()
