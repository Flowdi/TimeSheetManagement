from __future__ import annotations

import csv
import io
import unittest

from timesheet.reporting import REPORT_HEADERS, monthly_report_csv


class ReportingTests(unittest.TestCase):
    def test_monthly_report_csv_contains_all_report_columns(self):
        content = monthly_report_csv(
            [
                {
                    "display_name": "Jörg Müller",
                    "work_minutes": 480,
                    "overtime_minutes": -30,
                    "absence_days": 3,
                    "vacation_days": 1,
                    "holiday_days": 1,
                    "overtime_reduction_days": 1,
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
            ["2026-08", "Jörg Müller", "08:00 h", "-00:30 h", "3", "1", "1", "1", "2"],
        )

    def test_monthly_report_csv_can_export_empty_report(self):
        content = monthly_report_csv([], 2026, 8)
        rows = list(csv.reader(io.StringIO(content), delimiter=";"))
        self.assertEqual(rows, [list(REPORT_HEADERS)])


if __name__ == "__main__":
    unittest.main()
