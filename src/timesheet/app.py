from __future__ import annotations

import calendar
import json
import os
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .database import Database
from .service import ABSENCE_LABELS, EVENT_LABELS, TimeSheetService, format_minutes


STATUS_LABELS = {"pending": "Offen", "approved": "Genehmigt", "rejected": "Abgelehnt"}

THEMES = {
    "dark": {
        "bg": "#212121",
        "surface": "#2f2f2f",
        "surface_alt": "#383838",
        "text": "#ececec",
        "muted": "#b4b4b4",
        "accent": "#68d5ff",
        "accent_hover": "#9be5ff",
        "selected": "#164e63",
        "danger": "#ff8b8b",
    },
    "light": {
        "bg": "#f4f7f9",
        "surface": "#ffffff",
        "surface_alt": "#e8eef2",
        "text": "#17212b",
        "muted": "#52606d",
        "accent": "#008fbd",
        "accent_hover": "#00b7eb",
        "selected": "#c9effc",
        "danger": "#b42318",
    },
}


def app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "TimeSheetManagement"


class TimeSheetApp(tk.Tk):
    def __init__(self, db_path: Path | None = None):
        super().__init__()
        self.title("TimeSheet Management")
        self.geometry("1050x700")
        self.minsize(900, 600)
        self.db = Database(db_path or app_data_dir() / "timesheet.db")
        self.service = TimeSheetService(self.db)
        self.user = None
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.theme_name = self.load_theme()
        self.apply_theme()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        if self.service.has_users():
            self.show_login()
        else:
            self.show_first_run()

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    @property
    def settings_path(self) -> Path:
        return app_data_dir() / "settings.json"

    def load_theme(self) -> str:
        try:
            value = json.loads(self.settings_path.read_text(encoding="utf-8")).get("theme")
            return value if value in THEMES else "dark"
        except (OSError, ValueError, TypeError):
            return "dark"

    def set_theme(self, display_name: str):
        self.theme_name = "light" if display_name.lower().startswith("hell") else "dark"
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps({"theme": self.theme_name}, indent=2), encoding="utf-8"
        )
        self.apply_theme()

    def apply_theme(self):
        colors = THEMES[self.theme_name]
        self.configure(background=colors["bg"])
        common = {"background": colors["bg"], "foreground": colors["text"]}
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabel", **common, font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", **common, font=("Segoe UI", 20, "bold"))
        self.style.configure("Heading.TLabel", **common, font=("Segoe UI", 12, "bold"))
        self.style.configure(
            "Muted.TLabel", background=colors["bg"], foreground=colors["muted"]
        )
        self.style.configure(
            "Warning.TLabel", background=colors["bg"], foreground=colors["danger"],
            font=("Segoe UI", 11, "bold")
        )
        self.style.configure(
            "TButton", background=colors["surface"], foreground=colors["text"],
            bordercolor=colors["accent"], lightcolor=colors["accent"], darkcolor=colors["accent"],
            padding=(10, 7), font=("Segoe UI", 10), relief="solid", borderwidth=1,
        )
        self.style.map("TButton", background=[("active", colors["surface_alt"]), ("pressed", colors["selected"])], foreground=[("active", colors["accent_hover"])])
        self.style.configure("Action.TButton", padding=(15, 12), font=("Segoe UI", 11, "bold"), foreground=colors["accent"])
        self.style.configure("TEntry", fieldbackground=colors["surface"], foreground=colors["text"], insertcolor=colors["text"], bordercolor=colors["accent"], padding=6)
        self.style.configure("TCombobox", fieldbackground=colors["surface"], background=colors["surface"], foreground=colors["text"], arrowcolor=colors["accent"], bordercolor=colors["accent"], padding=5)
        self.style.map("TCombobox", fieldbackground=[("readonly", colors["surface"])], foreground=[("readonly", colors["text"])])
        self.option_add("*TCombobox*Listbox.background", colors["surface"])
        self.option_add("*TCombobox*Listbox.foreground", colors["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", colors["selected"])
        self.style.configure("TNotebook", background=colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=colors["surface"], foreground=colors["muted"], padding=(14, 9), bordercolor=colors["bg"])
        self.style.map("TNotebook.Tab", background=[("selected", colors["surface_alt"])], foreground=[("selected", colors["accent"])])
        self.style.configure("Treeview", background=colors["surface"], fieldbackground=colors["surface"], foreground=colors["text"], bordercolor=colors["accent"], rowheight=27)
        self.style.configure("Treeview.Heading", background=colors["surface_alt"], foreground=colors["accent"], bordercolor=colors["accent"], font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", colors["selected"])], foreground=[("selected", colors["text"])])
        self.style.configure("TLabelframe", background=colors["bg"], bordercolor=colors["accent"], relief="solid", borderwidth=1)
        self.style.configure(
            "TLabelframe.Label", background=colors["bg"], foreground=colors["accent"],
            font=("Segoe UI", 10, "bold")
        )
        self.style.configure("TPanedwindow", background=colors["bg"])

    def add_theme_selector(self, parent):
        wrapper = ttk.Frame(parent)
        ttk.Label(wrapper, text="Darstellung", style="Muted.TLabel").pack(side="left", padx=(0, 7))
        selector = ttk.Combobox(wrapper, state="readonly", width=9, values=("Dunkel", "Hell"))
        selector.set("Dunkel" if self.theme_name == "dark" else "Hell")
        selector.bind("<<ComboboxSelected>>", lambda _event: self.set_theme(selector.get()))
        selector.pack(side="left")
        return wrapper

    def show_first_run(self):
        self.clear()
        frame = ttk.Frame(self, padding=40)
        frame.place(relx=.5, rely=.45, anchor="center")
        ttk.Label(frame, text="Ersteinrichtung", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Lege das lokale Administratorkonto an.").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        fields = [("Benutzername", "username"), ("Anzeigename", "name"), ("Passwort (mind. 8 Zeichen)", "password")]
        entries = {}
        for row, (label, key) in enumerate(fields, 2):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 15), pady=6)
            entry = ttk.Entry(frame, width=32, show="*" if key == "password" else "")
            entry.grid(row=row, column=1, pady=6)
            entries[key] = entry

        def create():
            try:
                self.service.create_user(entries["username"].get(), entries["name"].get(), entries["password"].get(), "admin")
                messagebox.showinfo("Erstellt", "Administratorkonto wurde angelegt.")
                self.show_login()
            except Exception as exc:
                messagebox.showerror("Nicht möglich", str(exc))

        ttk.Button(frame, text="Einrichtung abschließen", command=create, style="Action.TButton").grid(row=5, column=0, columnspan=2, pady=20)
        self.add_theme_selector(frame).grid(row=6, column=0, columnspan=2, pady=(5, 0))

    def show_login(self):
        self.clear()
        self.user = None
        frame = ttk.Frame(self, padding=40)
        frame.place(relx=.5, rely=.45, anchor="center")
        ttk.Label(frame, text="TimeSheet Management", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 25))
        ttk.Label(frame, text="Benutzername").grid(row=1, column=0, sticky="w", padx=(0, 15), pady=7)
        username = ttk.Entry(frame, width=30)
        username.grid(row=1, column=1, pady=7)
        ttk.Label(frame, text="Passwort").grid(row=2, column=0, sticky="w", padx=(0, 15), pady=7)
        password = ttk.Entry(frame, width=30, show="*")
        password.grid(row=2, column=1, pady=7)

        def login(event=None):
            user = self.service.authenticate(username.get(), password.get())
            if not user:
                messagebox.showerror("Anmeldung fehlgeschlagen", "Benutzername oder Passwort ist falsch.")
                return
            self.user = user
            self.show_dashboard()

        password.bind("<Return>", login)
        ttk.Button(frame, text="Anmelden", command=login, style="Action.TButton").grid(row=3, column=0, columnspan=2, pady=20)
        self.add_theme_selector(frame).grid(row=4, column=0, columnspan=2)
        username.focus_set()

    def show_dashboard(self):
        self.clear()
        header = ttk.Frame(self, padding=(20, 12))
        header.pack(fill="x")
        ttk.Label(header, text=f"Hallo, {self.user['display_name']}", style="Heading.TLabel").pack(side="left")
        ttk.Button(header, text="Abmelden", command=self.show_login).pack(side="right")
        self.add_theme_selector(header).pack(side="right", padx=15)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.time_tab = ttk.Frame(notebook, padding=20)
        self.absence_tab = ttk.Frame(notebook, padding=20)
        self.correction_tab = ttk.Frame(notebook, padding=20)
        notebook.add(self.time_tab, text="Arbeitszeit")
        notebook.add(self.absence_tab, text="Abwesenheiten")
        notebook.add(self.correction_tab, text="Korrekturen")
        if self.user["role"] == "admin":
            self.admin_tab = ttk.Frame(notebook, padding=20)
            self.report_tab = ttk.Frame(notebook, padding=20)
            notebook.add(self.admin_tab, text="Administration")
            notebook.add(self.report_tab, text="Auswertung")
            self.build_admin_tab()
            self.build_report_tab()
        self.build_time_tab()
        self.build_absence_tab()
        self.build_correction_tab()

    def build_time_tab(self):
        tab = self.time_tab
        ttk.Label(tab, text="Heutiger Arbeitstag", style="Title.TLabel").pack(anchor="w")
        self.clock_label = ttk.Label(tab, font=("Segoe UI", 26))
        self.clock_label.pack(anchor="w", pady=(8, 20))
        self.state_label = ttk.Label(tab, style="Heading.TLabel")
        self.state_label.pack(anchor="w", pady=5)
        self.summary_label = ttk.Label(tab, font=("Segoe UI", 12))
        self.summary_label.pack(anchor="w", pady=5)
        self.warning_label = ttk.Label(tab, style="Warning.TLabel")
        self.warning_label.pack(anchor="w", pady=(5, 20))
        buttons = ttk.Frame(tab)
        buttons.pack(anchor="w", pady=10)
        for col, (text, kind) in enumerate((("Arbeit beginnen", "work_start"), ("Pause beginnen", "break_start"), ("Pause beenden", "break_end"), ("Arbeit beenden", "work_end"))):
            ttk.Button(buttons, text=text, command=lambda k=kind: self.do_event(k), style="Action.TButton").grid(row=0, column=col, padx=(0, 10))
        ttk.Label(tab, text="Buchungen heute", style="Heading.TLabel").pack(anchor="w", pady=(30, 8))
        self.event_tree = ttk.Treeview(tab, columns=("time", "event"), show="headings", height=8)
        self.event_tree.heading("time", text="Uhrzeit")
        self.event_tree.heading("event", text="Ereignis")
        self.event_tree.column("time", width=130, stretch=False)
        self.event_tree.pack(fill="x")
        self.refresh_time()
        self.tick()

    def tick(self):
        if not self.user or not hasattr(self, "clock_label") or not self.clock_label.winfo_exists():
            return
        self.clock_label.configure(text=datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))
        self.after(1000, self.tick)

    def do_event(self, kind):
        try:
            self.service.record_event(self.user["id"], kind)
            self.refresh_time()
        except Exception as exc:
            messagebox.showerror("Buchung nicht möglich", str(exc))

    def refresh_time(self):
        state, summary = self.service.current_state(self.user["id"])
        labels = {None: "Noch nicht begonnen", "work_start": "Bei der Arbeit", "break_start": "In Pause", "break_end": "Bei der Arbeit", "work_end": "Arbeitstag beendet"}
        self.state_label.configure(text=f"Status: {labels[state]}")
        self.summary_label.configure(text=f"Arbeitszeit: {format_minutes(summary.work_minutes)}   Pause: {format_minutes(summary.break_minutes)}   Tagessaldo: {format_minutes(summary.overtime_minutes)}")
        self.warning_label.configure(text=" · ".join(summary.warnings))
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)
        for event in self.service.events_for_day(self.user["id"], date.today()):
            stamp = datetime.fromisoformat(event["occurred_at"]).strftime("%H:%M:%S")
            self.event_tree.insert("", "end", values=(stamp, EVENT_LABELS[event["event_type"]]))

    def build_absence_tab(self):
        tab = self.absence_tab
        ttk.Label(tab, text="Abwesenheit beantragen", style="Title.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 15))
        ttk.Label(tab, text="Art").grid(row=1, column=0, sticky="w")
        type_box = ttk.Combobox(tab, state="readonly", values=list(ABSENCE_LABELS.values()), width=22)
        type_box.current(0)
        type_box.grid(row=2, column=0, padx=(0, 10), sticky="w")
        ttk.Label(tab, text="Von (JJJJ-MM-TT)").grid(row=1, column=1, sticky="w")
        start = ttk.Entry(tab, width=16); start.insert(0, date.today().isoformat()); start.grid(row=2, column=1, padx=(0, 10))
        ttk.Label(tab, text="Bis (JJJJ-MM-TT)").grid(row=1, column=2, sticky="w")
        end = ttk.Entry(tab, width=16); end.insert(0, date.today().isoformat()); end.grid(row=2, column=2, padx=(0, 10))
        ttk.Label(tab, text="Bemerkung").grid(row=3, column=0, sticky="w", pady=(12, 0))
        reason = ttk.Entry(tab, width=65); reason.grid(row=4, column=0, columnspan=3, sticky="ew")

        def submit():
            try:
                kind = next(key for key, value in ABSENCE_LABELS.items() if value == type_box.get())
                self.service.request_absence(self.user["id"], kind, start.get(), end.get(), reason.get())
                messagebox.showinfo("Gesendet", "Der Antrag wurde zur Genehmigung eingereicht.")
                self.refresh_absences()
            except Exception as exc:
                messagebox.showerror("Nicht möglich", str(exc))
        ttk.Button(tab, text="Antrag einreichen", command=submit).grid(row=2, column=3, padx=10)
        ttk.Label(tab, text="Meine Anträge", style="Heading.TLabel").grid(row=5, column=0, columnspan=4, sticky="w", pady=(30, 8))
        self.absence_tree = ttk.Treeview(tab, columns=("type","start","end","status"), show="headings", height=13)
        for column, label in (("type","Art"),("start","Von"),("end","Bis"),("status","Status")):
            self.absence_tree.heading(column, text=label)
        self.absence_tree.grid(row=6, column=0, columnspan=4, sticky="nsew")
        tab.rowconfigure(6, weight=1); tab.columnconfigure(2, weight=1)
        self.refresh_absences()

    def refresh_absences(self):
        for item in self.absence_tree.get_children(): self.absence_tree.delete(item)
        for row in self.service.list_absences(self.user["id"]):
            self.absence_tree.insert("", "end", values=(ABSENCE_LABELS[row["absence_type"]],row["start_date"],row["end_date"],STATUS_LABELS[row["status"]]))

    def build_correction_tab(self):
        tab = self.correction_tab
        ttk.Label(tab, text="Zeitkorrektur beantragen", style="Title.TLabel").grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 15))
        defaults = (("Datum", date.today().isoformat()),("Beginn", "08:00"),("Ende", "16:30"),("Pause (Min.)", "30"))
        entries = {}
        for col, (label, default) in enumerate(defaults):
            ttk.Label(tab, text=label).grid(row=1, column=col, sticky="w")
            entry = ttk.Entry(tab, width=16); entry.insert(0, default); entry.grid(row=2, column=col, padx=(0,10)); entries[label]=entry
        ttk.Label(tab, text="Begründung").grid(row=3, column=0, sticky="w", pady=(12,0))
        reason = ttk.Entry(tab, width=70); reason.grid(row=4, column=0, columnspan=4, sticky="ew")
        def submit():
            try:
                self.service.request_correction(self.user["id"], entries["Datum"].get(), entries["Beginn"].get(), entries["Ende"].get(), entries["Pause (Min.)"].get(), reason.get())
                messagebox.showinfo("Gesendet", "Die Korrektur wurde zur Genehmigung eingereicht.")
                self.refresh_corrections()
            except Exception as exc: messagebox.showerror("Nicht möglich", str(exc))
        ttk.Button(tab, text="Korrektur einreichen", command=submit).grid(row=2, column=4)
        ttk.Label(tab, text="Meine Korrekturen", style="Heading.TLabel").grid(row=5, column=0, columnspan=5, sticky="w", pady=(30,8))
        self.correction_tree = ttk.Treeview(tab, columns=("date","start","end","break","status"), show="headings", height=13)
        for column,label in (("date","Datum"),("start","Beginn"),("end","Ende"),("break","Pause"),("status","Status")): self.correction_tree.heading(column,text=label)
        self.correction_tree.grid(row=6,column=0,columnspan=5,sticky="nsew")
        tab.rowconfigure(6,weight=1); tab.columnconfigure(3,weight=1)
        self.refresh_corrections()

    def refresh_corrections(self):
        for item in self.correction_tree.get_children(): self.correction_tree.delete(item)
        for row in self.service.list_corrections(self.user["id"]):
            self.correction_tree.insert("","end",values=(row["work_date"],row["proposed_start"],row["proposed_end"],row["proposed_break_minutes"],STATUS_LABELS[row["status"]]))

    def build_admin_tab(self):
        tab = self.admin_tab
        ttk.Label(tab, text="Administration", style="Title.TLabel").pack(anchor="w")
        user_box = ttk.LabelFrame(tab, text="Mitarbeiter anlegen", padding=12)
        user_box.pack(fill="x", pady=12)
        fields = {}
        for col, label in enumerate(("Benutzername", "Anzeigename", "Passwort")):
            ttk.Label(user_box, text=label).grid(row=0,column=col,sticky="w")
            entry=ttk.Entry(user_box,width=22,show="*" if label=="Passwort" else ""); entry.grid(row=1,column=col,padx=(0,10)); fields[label]=entry
        def add_user():
            try:
                self.service.create_user(fields["Benutzername"].get(), fields["Anzeigename"].get(), fields["Passwort"].get())
                messagebox.showinfo("Erstellt", "Mitarbeiterkonto wurde angelegt.")
            except Exception as exc: messagebox.showerror("Nicht möglich", str(exc))
        ttk.Button(user_box,text="Mitarbeiter anlegen",command=add_user).grid(row=1,column=3)
        panes = ttk.Panedwindow(tab, orient="horizontal"); panes.pack(fill="both",expand=True)
        absence_frame=ttk.LabelFrame(panes,text="Offene Abwesenheiten",padding=8); correction_frame=ttk.LabelFrame(panes,text="Offene Korrekturen",padding=8)
        panes.add(absence_frame,weight=1); panes.add(correction_frame,weight=1)
        self.pending_absence_tree=ttk.Treeview(absence_frame,columns=("name","type","range"),show="headings",height=12)
        for c,l in (("name","Mitarbeiter"),("type","Art"),("range","Zeitraum")): self.pending_absence_tree.heading(c,text=l)
        self.pending_absence_tree.pack(fill="both",expand=True)
        row=ttk.Frame(absence_frame); row.pack(fill="x",pady=6)
        ttk.Button(row,text="Genehmigen",command=lambda:self.review_selected_absence("approved")).pack(side="left")
        ttk.Button(row,text="Ablehnen",command=lambda:self.review_selected_absence("rejected")).pack(side="left",padx=6)
        self.pending_correction_tree=ttk.Treeview(correction_frame,columns=("name","date","hours"),show="headings",height=12)
        for c,l in (("name","Mitarbeiter"),("date","Datum"),("hours","Vorschlag")): self.pending_correction_tree.heading(c,text=l)
        self.pending_correction_tree.pack(fill="both",expand=True)
        row=ttk.Frame(correction_frame); row.pack(fill="x",pady=6)
        ttk.Button(row,text="Genehmigen",command=lambda:self.review_selected_correction("approved")).pack(side="left")
        ttk.Button(row,text="Ablehnen",command=lambda:self.review_selected_correction("rejected")).pack(side="left",padx=6)
        self.refresh_admin()

    def refresh_admin(self):
        for item in self.pending_absence_tree.get_children(): self.pending_absence_tree.delete(item)
        for row in self.service.list_absences(pending_only=True):
            self.pending_absence_tree.insert("","end",iid=str(row["id"]),values=(row["display_name"],ABSENCE_LABELS[row["absence_type"]],f"{row['start_date']} – {row['end_date']}"))
        for item in self.pending_correction_tree.get_children(): self.pending_correction_tree.delete(item)
        for row in self.service.list_corrections(pending_only=True):
            self.pending_correction_tree.insert("","end",iid=str(row["id"]),values=(row["display_name"],row["work_date"],f"{row['proposed_start']}–{row['proposed_end']}, {row['proposed_break_minutes']} Min."))

    def review_selected_absence(self,status):
        selection=self.pending_absence_tree.selection()
        if not selection: return
        self.service.review_absence(int(selection[0]),self.user["id"],status); self.refresh_admin()

    def review_selected_correction(self,status):
        selection=self.pending_correction_tree.selection()
        if not selection: return
        try: self.service.review_correction(int(selection[0]),self.user["id"],status); self.refresh_admin()
        except Exception as exc: messagebox.showerror("Nicht möglich",str(exc))

    def build_report_tab(self):
        tab=self.report_tab
        ttk.Label(tab,text="Monatsauswertung",style="Title.TLabel").pack(anchor="w")
        controls=ttk.Frame(tab); controls.pack(fill="x",pady=15)
        month=ttk.Spinbox(controls,from_=1,to=12,width=5); month.set(date.today().month); month.pack(side="left")
        year=ttk.Spinbox(controls,from_=2024,to=2100,width=7); year.set(date.today().year); year.pack(side="left",padx=8)
        self.report_tree=ttk.Treeview(tab,columns=("name","work","overtime","absence","warnings"),show="headings")
        for c,l in (("name","Mitarbeiter"),("work","Arbeitszeit"),("overtime","Saldo"),("absence","Abwesenheitstage"),("warnings","Tage mit Verstoß")): self.report_tree.heading(c,text=l)
        self.report_tree.pack(fill="both",expand=True)
        def refresh():
            for item in self.report_tree.get_children(): self.report_tree.delete(item)
            for row in self.service.report(int(year.get()),int(month.get())):
                self.report_tree.insert("","end",values=(row["display_name"],format_minutes(row["work_minutes"]),format_minutes(row["overtime_minutes"]),row["absence_days"],row["warning_days"]))
        ttk.Button(controls,text="Anzeigen",command=refresh).pack(side="left")
        refresh()


def main():
    TimeSheetApp().mainloop()


if __name__ == "__main__":
    main()
