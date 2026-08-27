from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .database import Database
from .security import hash_password, verify_password


EVENT_LABELS = {
    "work_start": "Arbeitsbeginn",
    "break_start": "Pausenbeginn",
    "break_end": "Pausenende",
    "work_end": "Arbeitsende",
}
ABSENCE_LABELS = {
    "vacation": "Urlaub",
    "holiday": "Feiertag",
    "overtime_reduction": "Überstundenabbau",
}
EXPECTED_NEXT = {
    None: "work_start",
    "work_start": "break_start",
    "break_start": "break_end",
    "break_end": "break_start",
    "work_end": "work_start",
}


@dataclass(frozen=True)
class DaySummary:
    work_minutes: int
    break_minutes: int
    overtime_minutes: int
    required_break_minutes: int
    warnings: tuple[str, ...]


def required_break_minutes(work_minutes: int) -> int:
    if work_minutes > 9 * 60:
        return 45
    if work_minutes > 6 * 60:
        return 30
    return 0


def summarize_events(events, now: datetime | None = None) -> DaySummary:
    now = now or datetime.now().astimezone()
    work = 0
    breaks = 0
    work_started = None
    break_started = None
    longest_work_block = 0
    block_started = None

    for event in events:
        occurred = datetime.fromisoformat(event["occurred_at"])
        kind = event["event_type"]
        if kind == "work_start":
            work_started = occurred
            block_started = occurred
        elif kind == "break_start" and work_started:
            work += max(0, int((occurred - work_started).total_seconds() // 60))
            if block_started:
                longest_work_block = max(longest_work_block, int((occurred - block_started).total_seconds() // 60))
            work_started = None
            block_started = None
            break_started = occurred
        elif kind == "break_end" and break_started:
            breaks += max(0, int((occurred - break_started).total_seconds() // 60))
            break_started = None
            work_started = occurred
            block_started = occurred
        elif kind == "work_end":
            if work_started:
                work += max(0, int((occurred - work_started).total_seconds() // 60))
                if block_started:
                    longest_work_block = max(longest_work_block, int((occurred - block_started).total_seconds() // 60))
            work_started = break_started = block_started = None

    if work_started:
        work += max(0, int((now - work_started).total_seconds() // 60))
        if block_started:
            longest_work_block = max(longest_work_block, int((now - block_started).total_seconds() // 60))
    if break_started:
        breaks += max(0, int((now - break_started).total_seconds() // 60))

    required = required_break_minutes(work)
    warnings = []
    if breaks < required:
        warnings.append(f"Pausenzeit unterschritten: {breaks} von {required} Minuten")
    if longest_work_block > 6 * 60:
        warnings.append("Mehr als 6 Stunden ohne Pause")
    if work > 10 * 60:
        warnings.append("Mehr als 10 Stunden Arbeitszeit")
    return DaySummary(work, breaks, work - 8 * 60, required, tuple(warnings))


class TimeSheetService:
    def __init__(self, db: Database):
        self.db = db

    def has_users(self) -> bool:
        return bool(self.db.scalar("SELECT COUNT(*) FROM users"))

    def create_user(self, username: str, display_name: str, password: str, role="employee"):
        username, display_name = username.strip(), display_name.strip()
        if not username or not display_name or len(password) < 8:
            raise ValueError("Name erforderlich; Passwort muss mindestens 8 Zeichen haben.")
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                (username, display_name, hash_password(password), role, self.db.now()),
            )

    def authenticate(self, username: str, password: str):
        rows = self.db.rows("SELECT * FROM users WHERE username=? AND active=1", (username.strip(),))
        return rows[0] if rows and verify_password(password, rows[0]["password_hash"]) else None

    def list_users(self):
        return self.db.rows("SELECT id,username,display_name,role,active FROM users ORDER BY display_name")

    def event_days(self, user_id: int):
        return [
            date.fromisoformat(row["work_date"])
            for row in self.db.rows(
                "SELECT DISTINCT substr(occurred_at,1,10) AS work_date FROM time_events "
                "WHERE user_id=? ORDER BY work_date",
                (user_id,),
            )
        ]

    def sheet_row_for_day(self, user_id: int, day: date) -> list:
        events = self.events_for_day(user_id, day)
        if not events:
            raise ValueError("Für diesen Tag sind keine Arbeitszeiten vorhanden.")
        summary = summarize_events(events)
        first_start = next(
            (row for row in events if row["event_type"] == "work_start"), None
        )
        work_end = next(
            (row for row in reversed(events) if row["event_type"] == "work_end"), None
        )
        last_type = events[-1]["event_type"]
        status = {
            "work_start": "Arbeitet",
            "break_start": "Pause",
            "break_end": "Arbeitet",
            "work_end": "Beendet",
        }[last_type]
        break_periods = []
        break_start = None
        for event in events:
            if event["event_type"] == "break_start":
                break_start = datetime.fromisoformat(event["occurred_at"]).strftime("%H:%M")
            elif event["event_type"] == "break_end" and break_start:
                break_end = datetime.fromisoformat(event["occurred_at"]).strftime("%H:%M")
                break_periods.append(f"{break_start}–{break_end}")
                break_start = None
        if break_start:
            break_periods.append(f"{break_start}–offen")
        weekdays = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
        return [
            day.isoformat(),
            weekdays[day.weekday()],
            datetime.fromisoformat(first_start["occurred_at"]).strftime("%H:%M:%S") if first_start else "",
            "; ".join(break_periods),
            summary.break_minutes,
            datetime.fromisoformat(work_end["occurred_at"]).strftime("%H:%M:%S") if work_end else "",
            format_minutes(summary.work_minutes),
            format_minutes(summary.overtime_minutes),
            status,
            " | ".join(summary.warnings),
            datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        ]

    def record_event(self, user_id: int, event_type: str, occurred_at: datetime | None = None):
        occurred_at = occurred_at or datetime.now().astimezone()
        day = occurred_at.date().isoformat()
        events = self.events_for_day(user_id, occurred_at.date())
        last = events[-1]["event_type"] if events else None
        expected = EXPECTED_NEXT.get(last)
        if event_type == "work_end" and last in {"work_start", "break_end"}:
            pass
        elif event_type != expected:
            raise ValueError(f"Aktion nicht möglich. Erwartet: {EVENT_LABELS.get(expected, 'Arbeitsbeginn')}.")
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO time_events(user_id,event_type,occurred_at) VALUES(?,?,?)",
                (user_id, event_type, occurred_at.isoformat(timespec="seconds")),
            )
            con.execute(
                "INSERT INTO audit_log(actor_user_id,action,details,created_at) VALUES(?,?,?,?)",
                (user_id, "time_event", f"{event_type} am {day}", self.db.now()),
            )

    def events_for_day(self, user_id: int, day: date):
        start = datetime.combine(day, time.min).astimezone().isoformat()
        end = datetime.combine(day + timedelta(days=1), time.min).astimezone().isoformat()
        return self.db.rows(
            "SELECT * FROM time_events WHERE user_id=? AND occurred_at>=? AND occurred_at<? ORDER BY occurred_at,id",
            (user_id, start, end),
        )

    def current_state(self, user_id: int):
        events = self.events_for_day(user_id, date.today())
        return (events[-1]["event_type"] if events else None), summarize_events(events)

    def request_absence(self, user_id, absence_type, start_date, end_date, reason=""):
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
        if end < start:
            raise ValueError("Das Enddatum liegt vor dem Startdatum.")
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO absence_requests(user_id,absence_type,start_date,end_date,reason,created_at) VALUES(?,?,?,?,?,?)",
                (user_id, absence_type, start.isoformat(), end.isoformat(), reason.strip(), self.db.now()),
            )

    def list_absences(self, user_id=None, pending_only=False):
        conditions, params = [], []
        if user_id is not None:
            conditions.append("a.user_id=?")
            params.append(user_id)
        if pending_only:
            conditions.append("a.status='pending'")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return self.db.rows(
            "SELECT a.*,u.display_name FROM absence_requests a JOIN users u ON u.id=a.user_id"
            + where + " ORDER BY a.created_at DESC", params,
        )

    def review_absence(self, request_id, admin_id, status):
        if status not in {"approved", "rejected"}:
            raise ValueError("Ungültiger Status")
        with self.db.connect() as con:
            con.execute(
                "UPDATE absence_requests SET status=?,reviewed_by=?,reviewed_at=? WHERE id=? AND status='pending'",
                (status, admin_id, self.db.now(), request_id),
            )

    def request_correction(self, user_id, work_date, start, end, break_minutes, reason):
        date.fromisoformat(work_date)
        time.fromisoformat(start)
        time.fromisoformat(end)
        if not reason.strip() or int(break_minutes) < 0:
            raise ValueError("Begründung und gültige Pausenzeit erforderlich.")
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO correction_requests(user_id,work_date,proposed_start,proposed_end,proposed_break_minutes,reason,created_at) VALUES(?,?,?,?,?,?,?)",
                (user_id, work_date, start, end, int(break_minutes), reason.strip(), self.db.now()),
            )

    def list_corrections(self, user_id=None, pending_only=False):
        conditions, params = [], []
        if user_id is not None:
            conditions.append("c.user_id=?")
            params.append(user_id)
        if pending_only:
            conditions.append("c.status='pending'")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return self.db.rows(
            "SELECT c.*,u.display_name FROM correction_requests c JOIN users u ON u.id=c.user_id"
            + where + " ORDER BY c.created_at DESC", params,
        )

    def review_correction(self, request_id, admin_id, status):
        rows = self.db.rows("SELECT * FROM correction_requests WHERE id=? AND status='pending'", (request_id,))
        if not rows:
            raise ValueError("Antrag nicht mehr offen.")
        row = rows[0]
        with self.db.connect() as con:
            con.execute(
                "UPDATE correction_requests SET status=?,reviewed_by=?,reviewed_at=? WHERE id=?",
                (status, admin_id, self.db.now(), request_id),
            )
            if status == "approved":
                start = datetime.fromisoformat(f"{row['work_date']}T{row['proposed_start']}").astimezone()
                end = datetime.fromisoformat(f"{row['work_date']}T{row['proposed_end']}").astimezone()
                break_start = start + (end - start - timedelta(minutes=row["proposed_break_minutes"])) / 2
                break_end = break_start + timedelta(minutes=row["proposed_break_minutes"])
                con.execute("DELETE FROM time_events WHERE user_id=? AND date(occurred_at)=?", (row["user_id"], row["work_date"]))
                for kind, stamp in (("work_start",start),("break_start",break_start),("break_end",break_end),("work_end",end)):
                    con.execute("INSERT INTO time_events(user_id,event_type,occurred_at,source,note) VALUES(?,?,?,?,?)", (row["user_id"],kind,stamp.isoformat(timespec="seconds"),"correction",f"Korrekturantrag #{request_id}"))
        return row["user_id"], date.fromisoformat(row["work_date"])

    def report(self, year: int, month: int):
        prefix = f"{year:04d}-{month:02d}"
        result = []
        for user in self.list_users():
            if not user["active"]:
                continue
            rows = self.db.rows("SELECT * FROM time_events WHERE user_id=? AND substr(occurred_at,1,7)=? ORDER BY occurred_at", (user["id"],prefix))
            grouped = {}
            for row in rows:
                grouped.setdefault(row["occurred_at"][:10], []).append(row)
            summaries = [summarize_events(events, datetime.fromisoformat(day + "T23:59:59").astimezone()) for day, events in grouped.items()]
            result.append({
                "display_name": user["display_name"],
                "work_minutes": sum(s.work_minutes for s in summaries),
                "overtime_minutes": sum(s.overtime_minutes for s in summaries),
                "warning_days": sum(bool(s.warnings) for s in summaries),
                "absence_days": self._approved_absence_weekdays(user["id"], year, month),
            })
        return result

    def _approved_absence_weekdays(self, user_id, year, month):
        first = date(year, month, 1)
        next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        days = set()
        for row in self.db.rows("SELECT start_date,end_date FROM absence_requests WHERE user_id=? AND status='approved'", (user_id,)):
            current, end = max(date.fromisoformat(row["start_date"]), first), min(date.fromisoformat(row["end_date"]), next_month - timedelta(days=1))
            while current <= end:
                if current.weekday() < 5:
                    days.add(current)
                current += timedelta(days=1)
        return len(days)


def format_minutes(minutes: int) -> str:
    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)
    return f"{sign}{minutes // 60:02d}:{minutes % 60:02d} h"
