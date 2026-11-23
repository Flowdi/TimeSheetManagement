import unittest

from timesheet.app import (
    NAVIGATION_TAB_PADDING,
    NAVIGATION_TAB_WIDTH,
    THEMES,
    TimeSheetApp,
    audit_action_label,
    parse_target_time,
)


class FakeStyle:
    def __init__(self):
        self.configured = {}
        self.mapped = {}

    def configure(self, name, **options):
        self.configured[name] = options

    def map(self, name, **options):
        self.mapped[name] = options


class FakeApp:
    theme_name = "dark"
    style = FakeStyle()

    def configure(self, **_options):
        pass

    def option_add(self, _pattern, _value):
        pass


class ThemeTests(unittest.TestCase):
    def test_audit_actions_have_readable_labels_and_safe_fallback(self):
        self.assertEqual(audit_action_label("password_reset"), "Passwort zurückgesetzt")
        self.assertEqual(audit_action_label("user_role_changed"), "Benutzerrolle geändert")
        self.assertEqual(
            audit_action_label("vacation_allowance_changed"),
            "Urlaubsanspruch geändert",
        )
        self.assertEqual(
            audit_action_label("daily_target_changed"),
            "Tägliche Sollzeit geändert",
        )
        self.assertEqual(audit_action_label("period_closed"), "Monat abgeschlossen")
        self.assertEqual(
            audit_action_label("period_reopened"), "Monat wieder geöffnet"
        )
        self.assertEqual(audit_action_label("future_action"), "future_action")

    def test_daily_target_time_parser(self):
        self.assertEqual(parse_target_time("07:30"), 450)
        self.assertEqual(parse_target_time("8:00"), 480)
        self.assertEqual(parse_target_time("24:00"), 1440)
        for value in ("", "7.5", "07:60", "00:00", "25:00"):
            with self.assertRaises(ValueError):
                parse_target_time(value)

    def test_both_themes_have_required_colors(self):
        required = {"bg", "surface", "surface_alt", "text", "muted", "accent", "accent_hover", "selected", "danger"}
        for colors in THEMES.values():
            self.assertEqual(set(colors), required)

    def test_theme_can_be_applied_without_conflicting_options(self):
        fake = FakeApp()
        TimeSheetApp.apply_theme(fake)
        self.assertEqual(fake.style.configured["TFrame"]["background"], "#212121")
        self.assertEqual(fake.style.configured["Muted.TLabel"]["foreground"], "#b4b4b4")

    def test_navigation_tabs_keep_same_size_in_every_state(self):
        fake = FakeApp()
        TimeSheetApp.apply_theme(fake)
        configured = fake.style.configured["App.TNotebook.Tab"]
        mapped = fake.style.mapped["App.TNotebook.Tab"]
        self.assertEqual(configured["width"], NAVIGATION_TAB_WIDTH)
        self.assertEqual(configured["padding"], NAVIGATION_TAB_PADDING)
        self.assertEqual(
            dict(mapped["padding"]),
            {"selected": NAVIGATION_TAB_PADDING, "!selected": NAVIGATION_TAB_PADDING},
        )
        self.assertEqual(
            dict(mapped["expand"]),
            {"selected": (0, 0, 0, 0), "!selected": (0, 0, 0, 0)},
        )


if __name__ == "__main__":
    unittest.main()
