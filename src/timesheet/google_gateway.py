from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = [
    "Datum",
    "Wochentag",
    "Arbeitsbeginn",
    "Pausen",
    "Pause gesamt (Min.)",
    "Arbeitsende",
    "Nettoarbeitszeit",
    "Überstunden",
    "Status",
    "Hinweise",
    "Synchronisiert am",
]
TITLE_ROW = 1
HEADER_ROW = 3
DATA_START_ROW = 4

DARK_BG = {"red": 0.129, "green": 0.129, "blue": 0.129}
DARK_SURFACE = {"red": 0.184, "green": 0.184, "blue": 0.184}
DARK_ALT = {"red": 0.153, "green": 0.153, "blue": 0.153}
LIGHT_TEXT = {"red": 0.925, "green": 0.925, "blue": 0.925}
MUTED_TEXT = {"red": 0.706, "green": 0.706, "blue": 0.706}
ACCENT = {"red": 0.408, "green": 0.835, "blue": 1.0}


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


def credential_kind(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise GoogleNotConfigured("Die Google-Zugangsdaten sind keine gültige JSON-Datei.") from exc
    kind = payload.get("type") if isinstance(payload, dict) else None
    if kind == "service_account":
        return "service_account"
    if isinstance(payload, dict) and ("installed" in payload or "web" in payload):
        return "oauth"
    raise GoogleNotConfigured("Unbekannter Typ der Google-Zugangsdaten.")


def automatic_sync_ready(config: GoogleConfig) -> bool:
    """Return whether a configured account can sync without user interaction."""
    if not config.configured:
        return False
    kind = credential_kind(config.credentials_path)
    return kind == "service_account" or config.token_path.is_file()


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
            from google.oauth2.service_account import Credentials as ServiceAccountCredentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GoogleDependencyMissing(
                "Google-Pakete fehlen. Führe '.\\install.ps1' aus."
            ) from exc
        return Request, Credentials, ServiceAccountCredentials, InstalledAppFlow, build

    def authorize(self, interactive: bool = True):
        self.ensure_configured()
        Request, Credentials, ServiceAccountCredentials, InstalledAppFlow, build = self._imports()
        if credential_kind(self.config.credentials_path) == "service_account":
            credentials = ServiceAccountCredentials.from_service_account_file(
                str(self.config.credentials_path), scopes=SCOPES
            )
            return build("sheets", "v4", credentials=credentials, cache_discovery=False)
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
            range=f"'{title}'!A{DATA_START_ROW}:A",
        ).execute().get("values", [])
        target_row = next(
            (index + DATA_START_ROW for index, value in enumerate(existing) if value and value[0] == row[0]),
            len(existing) + DATA_START_ROW,
        )
        values_api.update(
            spreadsheetId=self.config.spreadsheet_id,
            range=f"'{title}'!A{target_row}:K{target_row}",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        ).execute()
        return {"sheet_id": sheet_id, "sheet_title": title, "row": target_row}

    def initialize_template(self, title: str = "Vorlage"):
        """Turn the first completely blank worksheet into a dark-mode template."""
        service = self.authorize(interactive=False)
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=self.config.spreadsheet_id,
            includeGridData=True,
            ranges=["A1:K10"],
            fields="sheets(properties(sheetId,title),data.rowData.values.effectiveValue)",
        ).execute()
        sheets = spreadsheet.get("sheets", [])
        if not sheets:
            raise RuntimeError("Das Spreadsheet enthält keine Registerkarte.")
        first = sheets[0]
        values = first.get("data", [{}])[0].get("rowData", [])
        if any(cell.get("effectiveValue") for row in values for cell in row.get("values", [])):
            raise RuntimeError("Die erste Registerkarte enthält bereits Daten und wird nicht überschrieben.")
        clean_title = sanitize_sheet_title(title)
        self._format_sheet(service, first["properties"]["sheetId"], clean_title, rename=True)
        return clean_title

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
        self._format_sheet(service, sheet_id, title)
        return sheet_id

    def _format_sheet(self, service, sheet_id: int, title: str, rename: bool = False):
        column_widths = [105, 105, 115, 210, 145, 115, 145, 120, 115, 300, 175]
        requests = [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        **({"title": title} if rename else {}),
                        "gridProperties": {"frozenRowCount": HEADER_ROW, "hideGridlines": True},
                        "tabColorStyle": {"rgbColor": ACCENT},
                    },
                    "fields": "title,gridProperties.frozenRowCount,gridProperties.hideGridlines,tabColorStyle"
                    if rename else "gridProperties.frozenRowCount,gridProperties.hideGridlines,tabColorStyle",
                }
            },
            {"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)}, "mergeType": "MERGE_ALL"}},
            {"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)}, "mergeType": "MERGE_ALL"}},
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)},
                    "cell": {"userEnteredFormat": {"backgroundColor": DARK_BG, "textFormat": {"foregroundColor": LIGHT_TEXT, "fontFamily": "Arial", "fontSize": 10}, "verticalAlignment": "MIDDLE"}},
                    "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)},
                    "cell": {"userEnteredFormat": {"backgroundColor": DARK_BG, "horizontalAlignment": "LEFT", "textFormat": {"foregroundColor": ACCENT, "fontFamily": "Arial", "fontSize": 18, "bold": True}}},
                    "fields": "userEnteredFormat",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)},
                    "cell": {"userEnteredFormat": {"backgroundColor": DARK_BG, "textFormat": {"foregroundColor": MUTED_TEXT, "fontFamily": "Arial", "fontSize": 10, "italic": True}}},
                    "fields": "userEnteredFormat",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": HEADER_ROW - 1, "endRowIndex": HEADER_ROW, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)},
                    "cell": {"userEnteredFormat": {"backgroundColor": DARK_SURFACE, "horizontalAlignment": "CENTER", "textFormat": {"foregroundColor": ACCENT, "fontFamily": "Arial", "fontSize": 10, "bold": True}, "borders": {"bottom": {"style": "SOLID_MEDIUM", "color": ACCENT}}}},
                    "fields": "userEnteredFormat",
                }
            },
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 42}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 34}, "fields": "pixelSize"}},
            {"setBasicFilter": {"filter": {"range": {"sheetId": sheet_id, "startRowIndex": HEADER_ROW - 1, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)}}}},
            {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [{"sheetId": sheet_id, "startRowIndex": DATA_START_ROW - 1, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": len(HEADERS)}], "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=ISEVEN(ROW())"}]}, "format": {"backgroundColor": DARK_ALT}}}}},
            {"addConditionalFormatRule": {"index": 1, "rule": {"ranges": [{"sheetId": sheet_id, "startRowIndex": DATA_START_ROW - 1, "endRowIndex": 1000, "startColumnIndex": 8, "endColumnIndex": 9}], "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "Beendet"}]}, "format": {"backgroundColor": {"red": 0.10, "green": 0.35, "blue": 0.25}, "textFormat": {"foregroundColor": LIGHT_TEXT, "bold": True}}}}}},
            {"addConditionalFormatRule": {"index": 2, "rule": {"ranges": [{"sheetId": sheet_id, "startRowIndex": DATA_START_ROW - 1, "endRowIndex": 1000, "startColumnIndex": 8, "endColumnIndex": 9}], "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "Pause"}]}, "format": {"backgroundColor": {"red": 0.45, "green": 0.31, "blue": 0.08}, "textFormat": {"foregroundColor": LIGHT_TEXT, "bold": True}}}}}},
            {"addConditionalFormatRule": {"index": 3, "rule": {"ranges": [{"sheetId": sheet_id, "startRowIndex": DATA_START_ROW - 1, "endRowIndex": 1000, "startColumnIndex": 9, "endColumnIndex": 10}], "booleanRule": {"condition": {"type": "NOT_BLANK"}, "format": {"textFormat": {"foregroundColor": {"red": 1.0, "green": 0.55, "blue": 0.55}, "bold": True}}}}}},
        ]
        for index, width in enumerate(column_widths):
            requests.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": index, "endIndex": index + 1}, "properties": {"pixelSize": width}, "fields": "pixelSize"}})
        service.spreadsheets().batchUpdate(
            spreadsheetId=self.config.spreadsheet_id,
            body={"requests": requests},
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=self.config.spreadsheet_id,
            range=f"'{title}'!A1:K3",
            valueInputOption="RAW",
            body={"values": [[f"Arbeitszeitübersicht – {title}"], ["Sollzeit Mo–Fr: 08:00–16:30 Uhr · 8:00 h netto · Pause mindestens 30 Min."], HEADERS]},
        ).execute()
