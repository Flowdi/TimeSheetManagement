from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = [
    "Datum",
    "Arbeitsbeginn",
    "Arbeitsende",
    "Pause (Min.)",
    "Arbeitszeit",
    "Überstunden",
    "Status",
    "Warnungen",
    "Synchronisiert am",
]


@dataclass(frozen=True)
class GoogleConfig:
    credentials_path: Path
    token_path: Path
    spreadsheet_id: str

    @property
    def configured(self) -> bool:
        return bool(self.spreadsheet_id.strip() and self.credentials_path.is_file())


class GoogleNotConfigured(RuntimeError):
    pass


class GoogleDependencyMissing(RuntimeError):
    pass


def sanitize_sheet_title(value: str) -> str:
    title = re.sub(r"[\\/?*\[\]:]", "-", value).strip(" '\t")
    return (title or "Mitarbeiter")[:100]


class GoogleGateway:
    """Small adapter around the Google Sheets API.

    Authentication is intentionally initiated only by an administrator. Routine
    background sync reuses the resulting local token and never stores a Google
    password.
    """

    def __init__(self, config: GoogleConfig):
        self.config = config

    def ensure_configured(self):
        if not self.config.spreadsheet_id.strip():
            raise GoogleNotConfigured("Die Spreadsheet-ID fehlt.")
        if not self.config.credentials_path.is_file():
            raise GoogleNotConfigured(
                f"OAuth-Datei nicht gefunden: {self.config.credentials_path}"
            )

    @staticmethod
    def _imports():
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GoogleDependencyMissing(
                "Google-Pakete fehlen. Führe '.\\install.ps1' aus."
            ) from exc
        return Request, Credentials, InstalledAppFlow, build

    def authorize(self, interactive: bool = True):
        self.ensure_configured()
        Request, Credentials, InstalledAppFlow, build = self._imports()
        credentials = None
        if self.config.token_path.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self.config.token_path), SCOPES
                )
            except (ValueError, OSError):
                credentials = None
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            if not interactive:
                raise GoogleNotConfigured(
                    "Google ist noch nicht autorisiert. Bitte im Adminbereich verbinden."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.config.credentials_path), SCOPES
            )
            credentials = flow.run_local_server(port=0)
        self.config.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.token_path.write_text(credentials.to_json(), encoding="utf-8")
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def spreadsheet_title(self, interactive: bool = False) -> str:
        service = self.authorize(interactive=interactive)
        result = service.spreadsheets().get(
            spreadsheetId=self.config.spreadsheet_id,
            fields="properties.title",
        ).execute()
        return result["properties"]["title"]

    def sync_day(self, sheet_title: str, row: list, interactive: bool = False):
        service = self.authorize(interactive=interactive)
        title = sanitize_sheet_title(sheet_title)
        sheet_id = self._ensure_sheet(service, title)
        values_api = service.spreadsheets().values()
        existing = values_api.get(
            spreadsheetId=self.config.spreadsheet_id,
            range=f"'{title}'!A2:A",
        ).execute().get("values", [])
        target_row = next(
            (index + 2 for index, value in enumerate(existing) if value and value[0] == row[0]),
            len(existing) + 2,
        )
        values_api.update(
            spreadsheetId=self.config.spreadsheet_id,
            range=f"'{title}'!A{target_row}:I{target_row}",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        ).execute()
        return {"sheet_id": sheet_id, "sheet_title": title, "row": target_row}

    def _ensure_sheet(self, service, title: str) -> int:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=self.config.spreadsheet_id,
            fields="sheets.properties(sheetId,title)",
        ).execute()
        for sheet in spreadsheet.get("sheets", []):
            properties = sheet["properties"]
            if properties["title"] == title:
                return properties["sheetId"]
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=self.config.spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": title,
                                "gridProperties": {"rowCount": 1000, "columnCount": len(HEADERS)},
                                "tabColorStyle": {"rgbColor": {"red": 0.41, "green": 0.84, "blue": 1.0}},
                            }
                        }
                    }
                ]
            },
        ).execute()
        sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
        service.spreadsheets().values().update(
            spreadsheetId=self.config.spreadsheet_id,
            range=f"'{title}'!A1:I1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()
        service.spreadsheets().batchUpdate(
            spreadsheetId=self.config.spreadsheet_id,
            body={
                "requests": [
                    {"updateSheetProperties": {"properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
                    {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.13}, "textFormat": {"foregroundColor": {"red": 0.41, "green": 0.84, "blue": 1.0}, "bold": True}}}, "fields": "userEnteredFormat"}},
                    {"autoResizeDimensions": {"dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": len(HEADERS)}}},
                ]
            },
        ).execute()
        return sheet_id
