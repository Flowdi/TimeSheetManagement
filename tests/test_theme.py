import unittest

from timesheet.app import THEMES, TimeSheetApp


class FakeStyle:
    def __init__(self):
        self.configured = {}

    def configure(self, name, **options):
        self.configured[name] = options

    def map(self, _name, **_options):
        pass


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


if __name__ == "__main__":
    unittest.main()
