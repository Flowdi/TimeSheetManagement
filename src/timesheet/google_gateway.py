"""Vorbereitete Google-Schnittstelle.

Die eigentliche OAuth-Aktivierung folgt, sobald eine Desktop-OAuth-Datei aus der
Google Cloud Console lokal bereitgestellt wurde. Passwörter werden nie verwendet.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GoogleConfig:
    credentials_path: Path
    token_path: Path
    spreadsheet_id: str
    mailbox: str = "flowditsm@gmail.com"


class GoogleNotConfigured(RuntimeError):
    pass


class GoogleGateway:
    def __init__(self, config: GoogleConfig):
        self.config = config

    def ensure_configured(self):
        if not self.config.credentials_path.exists():
            raise GoogleNotConfigured(
                "Google OAuth ist noch nicht eingerichtet. credentials.json fehlt."
            )

    def sync(self):
        self.ensure_configured()
        raise GoogleNotConfigured(
            "Der Google-Sync wird in der nächsten Version nach OAuth-Freigabe aktiviert."
        )
