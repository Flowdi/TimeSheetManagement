from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BackupPolicy:
    enabled: bool
    directory: Path
    retention_count: int

    @classmethod
    def from_settings(cls, settings: dict, default_directory: Path):
        enabled = settings.get("automatic_backup_enabled", True)
        if not isinstance(enabled, bool):
            enabled = True
        raw_directory = settings.get("automatic_backup_directory", "")
        directory = Path(raw_directory) if isinstance(raw_directory, str) and raw_directory.strip() else default_directory
        try:
            retention = int(settings.get("automatic_backup_retention", 14))
        except (TypeError, ValueError):
            retention = 14
        if not 1 <= retention <= 3650:
            retention = 14
        return cls(enabled, directory, retention)

