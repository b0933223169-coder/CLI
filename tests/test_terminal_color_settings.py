import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("cool_app")
package.__path__ = [str(PROJECT_ROOT)]
package.__package__ = "cool_app"
sys.modules.setdefault("cool_app", package)

from cool_app import colors, colorpicker
from cool_app.colorpicker import _normalize_terminal_color
from cool_app.colors import DEFAULT_COLORS, TERMINAL_COLOR_KEYS


class TerminalColorSettingsTests(unittest.TestCase):
    def test_shared_terminal_color_entries_have_hex_defaults(self):
        self.assertEqual(len(TERMINAL_COLOR_KEYS), 3)
        for key in TERMINAL_COLOR_KEYS:
            self.assertRegex(DEFAULT_COLORS[key], r"^#[0-9a-fA-F]{6}$")

    def test_hex_values_are_normalized_to_full_lowercase_rgb(self):
        self.assertEqual(_normalize_terminal_color("#AbC"), "#aabbcc")
        self.assertEqual(_normalize_terminal_color("#12ABef"), "#12abef")

    def test_ansi_palette_values_convert_to_shared_rgb_values(self):
        self.assertEqual(_normalize_terminal_color("COLOR_196"), "#ff0000")
        self.assertEqual(_normalize_terminal_color("GREEN"), "#008000")
        self.assertEqual(_normalize_terminal_color("BG_021"), "#0000ff")

    def test_terminal_palette_rejects_reverse_mode(self):
        with self.assertRaisesRegex(ValueError, "不能使用終端反色"):
            _normalize_terminal_color("REVERSE")

    def test_cli_background_change_keeps_report_colors_and_saves_rgb(self):
        with tempfile.TemporaryDirectory() as directory:
            color_file = Path(directory) / "colors.json"
            color_file.write_text('{"title":"CYAN"}', encoding="utf-8")
            original_file = colors.COLORS_FILE
            original_cache = colors._COLORS_CACHE
            original_mtime = colors._COLORS_CACHE_MTIME
            try:
                colors.COLORS_FILE = color_file
                colors._COLORS_CACHE = None
                colors._COLORS_CACHE_MTIME = 0
                with patch("sys.stdout"):
                    colorpicker._color_main(
                        ["set", "terminal_background_color", "COLOR_196"]
                    )
                saved = colors.load_colors()
            finally:
                colors.COLORS_FILE = original_file
                colors._COLORS_CACHE = original_cache
                colors._COLORS_CACHE_MTIME = original_mtime

        self.assertEqual(saved["terminal_background_color"], "#ff0000")
        self.assertEqual(saved["title"], "CYAN")


if __name__ == "__main__":
    unittest.main()
