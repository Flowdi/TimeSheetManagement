import json
import tempfile
import unittest
from pathlib import Path

from timesheet.google_gateway import (
    HEADERS,
    GoogleConfig,
    automatic_sync_ready,
    credential_kind,
    sanitize_sheet_title,
)


class GoogleGatewayTests(unittest.TestCase):
    def test_sheet_title_removes_forbidden_characters(self):
        self.assertEqual(sanitize_sheet_title("Anna / Verkauf [A]"), "Anna - Verkauf -A-")

    def test_sheet_title_is_limited_to_google_maximum(self):
        self.assertEqual(len(sanitize_sheet_title("x" * 120)), 100)

    def test_daily_sheet_has_stable_columns(self):
        self.assertEqual(HEADERS[0], "Datum")
        self.assertEqual(HEADERS[-1], "Synchronisiert am")
        self.assertEqual(len(HEADERS), 11)

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

    def test_service_account_is_ready_without_oauth_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / "service-account.json"
            key.write_text(json.dumps({"type": "service_account"}), encoding="utf-8")
            config = GoogleConfig(key, root / "missing-token.json", "sheet-id")
            self.assertTrue(automatic_sync_ready(config))

    def test_desktop_oauth_requires_existing_token_for_background_sync(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / "credentials.json"
            token = root / "token.json"
            key.write_text(json.dumps({"installed": {}}), encoding="utf-8")
            config = GoogleConfig(key, token, "sheet-id")
            self.assertFalse(automatic_sync_ready(config))
            token.write_text("{}", encoding="utf-8")
            self.assertTrue(automatic_sync_ready(config))


if __name__ == "__main__":
    unittest.main()
