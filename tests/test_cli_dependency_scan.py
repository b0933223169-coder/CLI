import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("cool_app")
package.__path__ = [str(PROJECT_ROOT)]
package.__package__ = "cool_app"
sys.modules.setdefault("cool_app", package)

from cool_app.cli import _discovered_imports


class CliDependencyScanTests(unittest.TestCase):
    def test_does_not_require_dependencies_used_only_by_the_legacy_gui(self):
        imports = _discovered_imports()
        third_party_modules = {
            import_name
            for _, import_name, kind in imports
            if kind == "第三方套件"
        }

        self.assertFalse(any(name == "PyQt6" or name.startswith("PyQt6.") for name in third_party_modules))
        self.assertNotIn("pyte", third_party_modules)
        self.assertNotIn("winpty", third_party_modules)


if __name__ == "__main__":
    unittest.main()
