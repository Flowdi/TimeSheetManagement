from __future__ import annotations

import json
from pathlib import Path


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def update(self, **values) -> dict:
        settings = self.load()
        settings.update(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        return settings

