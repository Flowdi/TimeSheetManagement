from __future__ import annotations

import unittest

from timesheet.reminder_settings import BreakReminderSettings


class BreakReminderSettingsTests(unittest.TestCase):
    def test_defaults_enable_thirty_minute_notice(self):
        settings = BreakReminderSettings.from_settings({})
        self.assertTrue(settings.enabled)
        self.assertEqual(settings.notice_minutes, 30)

    def test_saved_values_are_loaded(self):
        settings = BreakReminderSettings.from_settings({
            "break_reminders_enabled": False,
            "break_reminder_notice_minutes": "15",
        })
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.notice_minutes, 15)

    def test_invalid_values_use_safe_defaults(self):
        for raw in (0, 61, "später", None):
            settings = BreakReminderSettings.from_settings({
                "break_reminders_enabled": "yes",
                "break_reminder_notice_minutes": raw,
            })
            self.assertTrue(settings.enabled)
            self.assertEqual(settings.notice_minutes, 30)


if __name__ == "__main__":
    unittest.main()
