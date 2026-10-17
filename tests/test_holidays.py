from __future__ import annotations

import unittest
from datetime import date

from timesheet.holidays import augsburg_holidays, easter_sunday


class HolidayTests(unittest.TestCase):
    def test_easter_sunday_for_known_years(self):
        self.assertEqual(easter_sunday(2024), date(2024, 3, 31))
        self.assertEqual(easter_sunday(2026), date(2026, 4, 5))
        self.assertEqual(easter_sunday(2038), date(2038, 4, 25))

    def test_movable_bavarian_holidays_follow_easter(self):
        holidays = augsburg_holidays(2026)
        self.assertEqual(holidays[date(2026, 4, 3)], "Karfreitag")
        self.assertEqual(holidays[date(2026, 4, 6)], "Ostermontag")
        self.assertEqual(holidays[date(2026, 5, 14)], "Christi Himmelfahrt")
        self.assertEqual(holidays[date(2026, 5, 25)], "Pfingstmontag")
        self.assertEqual(holidays[date(2026, 6, 4)], "Fronleichnam")

    def test_augsburg_specific_and_bavarian_fixed_holidays_are_included(self):
        holidays = augsburg_holidays(2026)
        self.assertEqual(holidays[date(2026, 8, 8)], "Augsburger Friedensfest")
        self.assertEqual(holidays[date(2026, 8, 15)], "Mariä Himmelfahrt")
        self.assertEqual(holidays[date(2026, 1, 6)], "Heilige Drei Könige")
        self.assertEqual(len(holidays), 14)


if __name__ == "__main__":
    unittest.main()
