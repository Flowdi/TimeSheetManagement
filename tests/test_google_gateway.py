import unittest

from timesheet.google_gateway import HEADERS, sanitize_sheet_title


class GoogleGatewayTests(unittest.TestCase):
    def test_sheet_title_removes_forbidden_characters(self):
        self.assertEqual(sanitize_sheet_title("Anna / Verkauf [A]"), "Anna - Verkauf -A-")

    def test_sheet_title_is_limited_to_google_maximum(self):
        self.assertEqual(len(sanitize_sheet_title("x" * 120)), 100)

    def test_daily_sheet_has_stable_columns(self):
        self.assertEqual(HEADERS[0], "Datum")
        self.assertEqual(HEADERS[-1], "Synchronisiert am")
        self.assertEqual(len(HEADERS), 9)


if __name__ == "__main__":
    unittest.main()
