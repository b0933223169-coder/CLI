import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("cool_app")
package.__path__ = [str(PROJECT_ROOT)]
package.__package__ = "cool_app"
sys.modules.setdefault("cool_app", package)

from cool_app.accounts import AccountManager


class AccountManagerSyncTests(unittest.TestCase):
    def test_refreshes_accounts_written_by_desktop_after_manager_startup(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            account_file = data_dir / "accounts.json"
            cookie_dir = data_dir / "cookies"
            account_file.write_text("[]", encoding="utf-8")
            manager = AccountManager(path=account_file, cookie_dir=cookie_dir)

            account_file.write_text(
                json.dumps(
                    [
                        {
                            "name": "new-account",
                            "email": "new@example.com",
                            "cookie_file": "cookies/new.txt",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(manager.list_accounts()[0]["email"], "new@example.com")
            self.assertEqual(manager.find("new-account")["email"], "new@example.com")


if __name__ == "__main__":
    unittest.main()
