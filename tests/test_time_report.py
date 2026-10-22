import contextlib
import io
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("cool_app")
package.__path__ = [str(PROJECT_ROOT)]
package.__package__ = "cool_app"
sys.modules.setdefault("cool_app", package)

from cool_app.commands.time_report import cmd_time


class FakeResponse:
    def __init__(self, url: str, html: str):
        self.url = url
        self.html = html

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self):
        return self.html.encode("utf-8")


class FakeAccountManager:
    def __init__(self, cookie_path: Path):
        self.cookie_path = cookie_path
        self.account = {
            "name": "student",
            "email": "student@example.com",
            "user_id": "12345"
        }

    def list_accounts(self):
        return [self.account]

    def get_cookie_path(self, _account_id):
        return self.cookie_path

    def get_account_for_cookie(self, _cookie_path):
        return self.account


class TimeReportTests(unittest.TestCase):
    def test_fetches_and_parses_time_report_html_with_cookie_without_playwright(self):
        current_month = datetime.now().strftime("%Y/%m")
        html = f"""
            <html><body><table id="sort-table"><tbody><tr>
            <td>{current_month}</td><td>7 小時 30 分</td><td>3 小時</td><td>2 小時</td>
            </tr></tbody></table></body></html>
        """
        target_url = (
            "https://www.coolenglish.edu.tw/time/time_view_detail_by_people.php?id=12345"
        )
        cookie_seen = []
        sync_playwright = Mock(side_effect=AssertionError("time report must not start a browser"))
        playwright_package = types.ModuleType("playwright")
        playwright_package.__path__ = []
        playwright_api = types.ModuleType("playwright.sync_api")
        playwright_api.sync_playwright = sync_playwright

        class FakeOpener:
            def open(self, request, timeout):
                self_timeout[0] = timeout
                cookie_seen.append(request.get_header("Cookie"))
                return FakeResponse(target_url, html)

        self_timeout = [0]
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = Path(directory) / "student.txt"
            cookie_path.write_text(
                ".coolenglish.edu.tw\tTRUE\t/\tTRUE\t0\tMoodleSession\tmock-session\n",
                encoding="utf-8"
            )
            manager = FakeAccountManager(cookie_path)
            output = io.StringIO()
            with (
                patch("urllib.request.build_opener", return_value=FakeOpener()) as build_opener,
                patch("cool_app.commands.time_report.note"),
                patch("cool_app.commands.time_report.status_line"),
                patch.dict(
                    sys.modules,
                    {"playwright": playwright_package, "playwright.sync_api": playwright_api}
                ),
                contextlib.redirect_stdout(output)
            ):
                cmd_time(manager, [])

        self.assertEqual(build_opener.call_count, 1)
        self.assertEqual(self_timeout[0], 20)
        self.assertEqual(cookie_seen, ["MoodleSession=mock-session"])
        self.assertIn(current_month, output.getvalue())
        self.assertIn("7 小時 30 分", output.getvalue())
        sync_playwright.assert_not_called()


if __name__ == "__main__":
    unittest.main()
