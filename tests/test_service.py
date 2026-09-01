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

    def test_user_can_change_own_password(self):
        self.service.change_password(self.user["id"], "Sicher123!", "NochSicherer456!")
        self.assertIsNone(self.service.authenticate("anna", "Sicher123!"))
        self.assertIsNotNone(self.service.authenticate("anna", "NochSicherer456!"))
        audit = self.db.rows(
            "SELECT action FROM audit_log WHERE actor_user_id=? ORDER BY id DESC",
            (self.user["id"],),
        )
        self.assertEqual(audit[0]["action"], "password_changed")

    def test_password_change_rejects_wrong_current_password(self):
        with self.assertRaisesRegex(ValueError, "bisherige Passwort"):
            self.service.change_password(self.user["id"], "falsch", "NochSicherer456!")
        self.assertIsNotNone(self.service.authenticate("anna", "Sicher123!"))

    def test_password_change_rejects_short_or_reused_password(self):
        with self.assertRaisesRegex(ValueError, "mindestens 8"):
            self.service.change_password(self.user["id"], "Sicher123!", "kurz")
        with self.assertRaisesRegex(ValueError, "unterscheiden"):
            self.service.change_password(self.user["id"], "Sicher123!", "Sicher123!")

    def test_event_order_is_enforced(self):
        with self.assertRaises(ValueError):
            self.service.record_event(self.user["id"], "break_start")

    def test_time_event_is_persisted_in_sync_queue(self):
        timestamp = datetime.fromisoformat("2026-08-14T08:00:00").astimezone()
        self.service.record_event(self.user["id"], "work_start", timestamp)
        jobs = self.service.due_sync_jobs(force=True)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["work_date"], "2026-08-14")
        self.assertEqual(jobs[0]["status"], "pending")

    def test_failed_sync_is_retained_and_can_be_completed(self):
        day = datetime.fromisoformat("2026-08-14").date()
        self.service.enqueue_sync(self.user["id"], day)
        self.service.mark_sync_failure(self.user["id"], day, "Netzwerk nicht erreichbar")
        failed = self.service.due_sync_jobs(force=True)[0]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["attempts"], 1)
        self.assertIn("Netzwerk", failed["last_error"])
        self.service.mark_sync_success(self.user["id"], day)
        self.assertEqual(self.service.sync_stats(), {"pending": 0, "failed": 0, "synced": 1})

    def test_new_booking_resets_failed_sync_for_same_day(self):
        day = datetime.fromisoformat("2026-08-14").date()
        self.service.enqueue_sync(self.user["id"], day)
        self.service.mark_sync_failure(self.user["id"], day, "vorheriger Fehler")
        self.service.record_event(
            self.user["id"], "work_start", datetime.fromisoformat("2026-08-14T08:00:00").astimezone()
        )
        job = self.service.due_sync_jobs(force=True)[0]
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["attempts"], 0)
        self.assertEqual(job["last_error"], "")

    def test_existing_events_are_backfilled_on_database_upgrade(self):
        timestamp = datetime.fromisoformat("2026-08-14T08:00:00").astimezone()
        self.service.record_event(self.user["id"], "work_start", timestamp)
        with self.db.connect() as connection:
            connection.execute("DELETE FROM sync_queue")
        upgraded = TimeSheetService(Database(self.db.path))
        jobs = upgraded.due_sync_jobs(force=True)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["work_date"], "2026-08-14")

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
        self.assertEqual(
            sheet_row[:9],
            [day, "Freitag", "08:00:00", "12:00–12:30", 30, "16:30:00", "08:00 h", "00:00 h", "Beendet"],
        )

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

    def test_absence_cannot_be_reviewed_twice(self):
        self.service.create_user("admin", "Admin", "Sicher123!", "admin")
        admin = self.service.authenticate("admin", "Sicher123!")
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        request = self.service.list_absences(self.user["id"])[0]
        self.service.review_absence(request["id"], admin["id"], "approved")
        with self.assertRaisesRegex(ValueError, "nicht mehr offen"):
            self.service.review_absence(request["id"], admin["id"], "rejected")
        self.assertEqual(self.service.list_absences(self.user["id"])[0]["status"], "approved")

    def test_employee_cannot_review_absence(self):
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        request = self.service.list_absences(self.user["id"])[0]
        with self.assertRaisesRegex(PermissionError, "Administratorkonto"):
            self.service.review_absence(request["id"], self.user["id"], "approved")
        self.assertEqual(self.service.list_absences(self.user["id"])[0]["status"], "pending")

    def test_absence_rejects_overlapping_active_request(self):
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        with self.assertRaisesRegex(ValueError, "bereits ein offener oder genehmigter"):
            self.service.request_absence(
                self.user["id"], "overtime_reduction", "2026-08-21", "2026-08-24"
            )
        self.service.request_absence(
            self.user["id"], "overtime_reduction", "2026-08-22", "2026-08-24"
        )
        self.assertEqual(len(self.service.list_absences(self.user["id"])), 2)

    def test_absence_rejects_unknown_type(self):
        with self.assertRaisesRegex(ValueError, "Unbekannte Abwesenheitsart"):
            self.service.request_absence(
                self.user["id"], "sick_leave", "2026-08-17", "2026-08-18"
            )
        self.assertEqual(self.service.list_absences(self.user["id"]), [])

    def test_rejected_absence_period_can_be_requested_again(self):
        self.service.create_user("admin", "Admin", "Sicher123!", "admin")
        admin = self.service.authenticate("admin", "Sicher123!")
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        request = self.service.list_absences(self.user["id"])[0]
        self.service.review_absence(request["id"], admin["id"], "rejected")
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        self.assertEqual(len(self.service.list_absences(self.user["id"])), 2)

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

    def test_reviews_reject_unknown_status(self):
        self.service.create_user("admin", "Admin", "Sicher123!", "admin")
        admin = self.service.authenticate("admin", "Sicher123!")
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        absence = self.service.list_absences(self.user["id"])[0]
        with self.assertRaisesRegex(ValueError, "Ungültiger Status"):
            self.service.review_absence(absence["id"], admin["id"], "archived")

        self.service.request_correction(
            self.user["id"], "2026-08-13", "08:00", "16:30", 30, "Test"
        )
        correction = self.service.list_corrections(self.user["id"])[0]
        with self.assertRaisesRegex(ValueError, "Ungültiger Status"):
            self.service.review_correction(correction["id"], admin["id"], "archived")

    def test_admin_reviews_are_written_to_audit_log(self):
        self.service.create_user("admin", "Admin", "Sicher123!", "admin")
        admin = self.service.authenticate("admin", "Sicher123!")
        self.service.request_absence(
            self.user["id"], "vacation", "2026-08-17", "2026-08-21"
        )
        absence = self.service.list_absences(self.user["id"])[0]
        self.service.review_absence(absence["id"], admin["id"], "rejected")

        self.service.request_correction(
            self.user["id"], "2026-08-13", "08:00", "16:30", 30, "Test"
        )
        correction = self.service.list_corrections(self.user["id"])[0]
        self.service.review_correction(correction["id"], admin["id"], "rejected")

        entries = self.db.rows(
            "SELECT action,details FROM audit_log WHERE actor_user_id=? ORDER BY id",
            (admin["id"],),
        )
        self.assertEqual(
            [entry["action"] for entry in entries],
            ["absence_reviewed", "correction_reviewed"],
        )
        self.assertTrue(all("rejected" in entry["details"] for entry in entries))

    def test_correction_rejects_end_before_start(self):
        with self.assertRaisesRegex(ValueError, "nach dem Arbeitsbeginn"):
            self.service.request_correction(
                self.user["id"], "2026-08-13", "16:30", "08:00", 30, "Zeiten vertauscht"
            )

    def test_correction_rejects_invalid_break_duration(self):
        with self.assertRaisesRegex(ValueError, "ganze Minutenzahl"):
            self.service.request_correction(
                self.user["id"], "2026-08-13", "08:00", "16:30", "eine halbe Stunde", "Test"
            )
        with self.assertRaisesRegex(ValueError, "kürzer als die Anwesenheitszeit"):
            self.service.request_correction(
                self.user["id"], "2026-08-13", "08:00", "08:30", 30, "Test"
            )


if __name__ == "__main__":
    unittest.main()
