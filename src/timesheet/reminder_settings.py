from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BreakReminderSettings:
    enabled: bool = True
    notice_minutes: int = 30

    @classmethod
    def from_settings(cls, settings: dict):
        enabled = settings.get("break_reminders_enabled", True)
        if not isinstance(enabled, bool):
            enabled = True
        try:
            notice_minutes = int(settings.get("break_reminder_notice_minutes", 30))
        except (TypeError, ValueError):
            notice_minutes = 30
        if not 5 <= notice_minutes <= 60:
            notice_minutes = 30
        return cls(enabled=enabled, notice_minutes=notice_minutes)
