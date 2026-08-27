import json
import tempfile
import unittest
from pathlib import Path

from timesheet.google_gateway import HEADERS, credential_kind, sanitize_sheet_title


class GoogleGatewayTests(unittest.TestCase):
    def test_sheet_title_removes_forbidden_characters(self):
        self.assertEqual(sanitize_sheet_title("Anna / Verkauf [A]"), "Anna - Verkauf -A-")

    def test_sheet_title_is_limited_to_google_maximum(self):
        self.assertEqual(len(sanitize_sheet_title("x" * 120)), 100)

    def test_daily_sheet_has_stable_columns(self):
        self.assertEqual(HEADERS[0], "Datum")
        self.assertEqual(HEADERS[-1], "Synchronisiert am")
        self.assertEqual(len(HEADERS), 9)

    def test_service_account_file_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.json"
            path.write_text(json.dumps({"type": "service_account"}), encoding="utf-8")
            self.assertEqual(credential_kind(path), "service_account")

    def test_desktop_oauth_file_is_still_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            path.write_text(json.dumps({"installed": {}}), encoding="utf-8")
            self.assertEqual(credential_kind(path), "oauth")


if __name__ == "__main__":
    unittest.main()
