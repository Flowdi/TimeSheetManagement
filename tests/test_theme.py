import unittest

from timesheet.app import (
    NAVIGATION_TAB_PADDING,
    NAVIGATION_TAB_WIDTH,
    THEMES,
    TimeSheetApp,
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
