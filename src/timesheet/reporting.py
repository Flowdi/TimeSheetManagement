from __future__ import annotations

import csv
import io

from .service import format_minutes


REPORT_HEADERS = (
    "Zeitraum",
    "Mitarbeiter",
    "Arbeitszeit",
    "Saldo",
    "Abwesenheitstage",
    "Urlaubstage",
    "Feiertage",
    "Überstundenabbau",
    "Ruhezeitverstöße",
    "Tage mit Verstoß",
)


def monthly_report_csv(rows, year: int, month: int) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(REPORT_HEADERS)
    period = f"{int(year):04d}-{int(month):02d}"
    for row in rows:
        writer.writerow(
            (
                period,
                row["display_name"],
                format_minutes(row["work_minutes"]),
                format_minutes(row["overtime_minutes"]),
                row["absence_days"],
                row["vacation_days"],
                row["holiday_days"],
                row["overtime_reduction_days"],
                row["rest_violation_days"],
                row["warning_days"],
            )
        )
    return output.getvalue()


def audit_entries_csv(entries) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(("Zeitpunkt", "Akteur", "Aktion", "Details"))
    for entry in entries:
        writer.writerow((
            entry["created_at"], entry["actor_name"],
            entry.get("action_label", entry["action"]), entry["details"],
        ))
    return output.getvalue()


def system_diagnostics_text(diagnostics) -> str:
    """Format system diagnostics for display or a future support export."""
    sync = diagnostics["sync"]
    integrity = "OK" if diagnostics["integrity"] == "ok" else diagnostics["integrity"]
    size_kib = diagnostics["size_bytes"] / 1024
    return "\n".join((
        f"Datenbankintegrität: {integrity}",
        f"Fremdschlüsselfehler: {diagnostics['foreign_key_errors']}",
        f"Journalmodus: {diagnostics['journal_mode']}",
        f"Datenbankgröße: {size_kib:.1f} KiB",
        "",
        f"Benutzer: {diagnostics['active_users']} aktiv / {diagnostics['total_users']} gesamt",
        f"Zeitbuchungen: {diagnostics['time_events']}",
        f"Offene Abwesenheiten: {diagnostics['pending_absences']}",
        f"Offene Korrekturen: {diagnostics['pending_corrections']}",
        "",
        f"Google-Sync: {sync['pending']} offen, {sync['failed']} fehlgeschlagen, "
        f"{sync['synced']} synchronisiert",
    ))
