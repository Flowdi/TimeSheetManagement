from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from timesheet.database import Database
from timesheet.service import TimeSheetService, required_break_minutes, summarize_events


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        self.service = TimeSheetService(self.db)
        self.service.create_user("anna", "Anna", "Sicher123!", "employee")
        self.user = self.service.authenticate("anna", "Sicher123!")

    def tearDown(self):
        self.temp.cleanup()

    def test_authentication(self):
        self.assertIsNotNone(self.user)
        self.assertIsNone(self.service.authenticate("anna", "falsch"))

    def test_event_order_is_enforced(self):
        with self.assertRaises(ValueError):
            self.service.record_event(self.user["id"], "break_start")

    def test_complete_workday_summary(self):
        day = "2026-08-14"
        for kind, stamp in (
            ("work_start", "08:00:00"),
            ("break_start", "12:00:00"),
            ("break_end", "12:30:00"),
            ("work_end", "16:30:00"),
        ):
            self.service.record_event(
                self.user["id"], kind, datetime.fromisoformat(f"{day}T{stamp}").astimezone()
            )
        events = self.service.events_for_day(self.user["id"], datetime.fromisoformat(day).date())
        result = summarize_events(events)
        self.assertEqual(result.work_minutes, 480)
        self.assertEqual(result.break_minutes, 30)
        self.assertEqual(result.overtime_minutes, 0)
        self.assertEqual(result.warnings, ())
        sheet_row = self.service.sheet_row_for_day(
            self.user["id"], datetime.fromisoformat(day).date()
        )
        self.assertEqual(sheet_row[:7], [day, "08:00:00", "16:30:00", 30, "08:00 h", "00:00 h", "Beendet"])

    def test_break_thresholds(self):
        self.assertEqual(required_break_minutes(360), 0)
        self.assertEqual(required_break_minutes(361), 30)
        self.assertEqual(required_break_minutes(540), 30)
        self.assertEqual(required_break_minutes(541), 45)

    def test_absence_approval(self):
        self.service.create_user("admin", "Admin", "Sicher123!", "admin")
        admin = self.service.authenticate("admin", "Sicher123!")
        self.service.request_absence(self.user["id"], "vacation", "2026-08-17", "2026-08-21")
        request = self.service.list_absences(self.user["id"])[0]
        self.service.review_absence(request["id"], admin["id"], "approved")
        self.assertEqual(self.service.list_absences(self.user["id"])[0]["status"], "approved")
        anna_report = next(
            row for row in self.service.report(2026, 8) if row["display_name"] == "Anna"
        )
        self.assertEqual(anna_report["absence_days"], 5)

    def test_approved_correction_creates_events(self):
        self.service.create_user("admin", "Admin", "Sicher123!", "admin")
        admin = self.service.authenticate("admin", "Sicher123!")
        self.service.request_correction(
            self.user["id"], "2026-08-13", "08:00", "16:30", 30, "Buchung vergessen"
        )
        request = self.service.list_corrections(self.user["id"])[0]
        self.service.review_correction(request["id"], admin["id"], "approved")
        events = self.service.events_for_day(self.user["id"], datetime.fromisoformat("2026-08-13").date())
        self.assertEqual([row["event_type"] for row in events], ["work_start", "break_start", "break_end", "work_end"])
        self.assertTrue(all(row["source"] == "correction" for row in events))


if __name__ == "__main__":
    unittest.main()
