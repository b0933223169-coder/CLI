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

from cool_app.commands import urls
from cool_app.commands.account import cmd_name


class CourseGroupTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_urls_file = urls.URLS_FILE
        urls.URLS_FILE = Path(self.temp_dir.name) / "urls.txt"

    def tearDown(self):
        urls.URLS_FILE = self.old_urls_file
        self.temp_dir.cleanup()

    def test_loads_legacy_flat_urls_and_preserves_named_groups(self):
        urls.URLS_FILE.write_text(
            "# old list\nhttps://example.com/legacy?id=4\n"
            "# group: %E5%BD%B1%E7%89%87\nhttps://example.com/movie?id=5\n",
            encoding="utf-8",
        )

        self.assertEqual(
            urls.load_course_groups(),
            [
                {"name": "未分類", "urls": ["https://example.com/legacy?id=4"]},
                {"name": "影片", "urls": ["https://example.com/movie?id=5"]},
            ],
        )

        urls.save_course_groups(urls.load_course_groups())
        serialized = urls.URLS_FILE.read_text(encoding="utf-8")
        self.assertIn("# group: %E5%BD%B1%E7%89%87", serialized)
        self.assertNotIn("# category:", serialized)

    def test_loads_separate_categories_and_group_names(self):
        urls.URLS_FILE.write_text(
            "# group: %E8%AA%B2%E7%A8%8B%E7%B5%84\n"
            "# category: %E8%8B%B1%E6%96%87\n"
            "https://example.com/course?id=1\n",
            encoding="utf-8",
        )
        self.assertEqual(
            urls.load_course_groups(),
            [
                {
                    "category": "英文",
                    "name": "課程組",
                    "urls": ["https://example.com/course?id=1"],
                }
            ],
        )
        urls.save_course_groups(urls.load_course_groups())
        self.assertIn(
            "# category: %E8%8B%B1%E6%96%87",
            urls.URLS_FILE.read_text(encoding="utf-8"),
        )

    def test_remove_by_category_deletes_all_matching_links(self):
        urls.save_course_groups(
            [
                {
                    "category": "英文",
                    "name": "課程組 A",
                    "urls": ["https://example.com/a", "https://example.com/b"],
                },
                {
                    "category": "英文",
                    "name": "課程組 B",
                    "urls": ["https://example.com/c"],
                },
                {
                    "category": "影片",
                    "name": "影片",
                    "urls": ["https://example.com/movie"],
                },
            ]
        )
        with patch("builtins.input", side_effect=["分類:英文", "y"]):
            urls._remove_course_url()
        self.assertEqual(
            urls.load_course_groups(),
            [
                {
                    "category": "影片",
                    "name": "影片",
                    "urls": ["https://example.com/movie"],
                }
            ],
        )

    def test_remove_by_link_index_still_deletes_only_selected_link(self):
        urls.save_course_groups(
            [
                {
                    "category": "英文",
                    "name": "課程組",
                    "urls": ["https://example.com/a", "https://example.com/b"],
                }
            ]
        )
        with patch("builtins.input", side_effect=["2", "y"]):
            urls._remove_course_url()
        self.assertEqual(
            urls.load_course_groups(),
            [
                {
                    "category": "英文",
                    "name": "課程組",
                    "urls": ["https://example.com/a"],
                }
            ],
        )

    def test_auto_group_names_get_incremented_suffixes(self):
        groups = [{"name": "學習", "urls": ["https://example.com/1"]}]
        self.assertEqual(urls._unique_group_name("學習", groups), "學習(1)")
        groups.append({"name": "學習(1)", "urls": ["https://example.com/2"]})
        self.assertEqual(urls._unique_group_name("學習", groups), "學習(2)")

    def test_course_group_autodetection_uses_authenticated_page_title_only(self):
        cookie_path = Path(self.temp_dir.name) / "cookies.txt"
        cookie_path.write_text(
            ".coolenglish.edu.tw\tTRUE\t/\tTRUE\t0\tMoodleSession\tsession\n",
            encoding="utf-8",
        )

        class Manager:
            def list_accounts(self):
                return [{"name": "student"}]

            def get_cookie_path(self, _name):
                return cookie_path

        class Response:
            def __init__(self, url, body):
                self.url = url
                self.body = body.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def geturl(self):
                return self.url

            def read(self, _limit):
                return self.body

        responses = [
            Response("https://www.coolenglish.edu.tw/my/", '<script>{"userId":42}</script>'),
            Response(
                "https://www.coolenglish.edu.tw/movie?id=321",
                "<html><title>歡樂電影城 - Cool English</title></html>",
            ),
        ]

        class Opener:
            def open(self, _request, timeout):
                self_timeout.append(timeout)
                requests.append(_request)
                return responses.pop(0)

        self_timeout = []
        requests = []
        manager = Manager()
        with patch.object(
            urls.urllib.request, "build_opener", return_value=Opener()
        ) as build_opener:
            self.assertEqual(
                urls._derive_course_group_name(
                    "https://www.coolenglish.edu.tw/movie?id=321", manager
                ),
                "影片",
            )
        build_opener.assert_called_once()
        self.assertEqual(self_timeout, [8, 8])
        self.assertTrue(requests[0].get_header("Cookie"))

    def test_invalid_cookie_falls_back_to_first_course_id_without_network(self):
        cookie_path = Path(self.temp_dir.name) / "cookies.txt"
        cookie_path.write_text(
            ".coolenglish.edu.tw\tTRUE\t/\tTRUE\t0\tMoodleSession\t\n",
            encoding="utf-8",
        )

        class Manager:
            def list_accounts(self):
                return [{"name": "student"}]

            def get_cookie_path(self, _name):
                return cookie_path

        with patch.object(urls.urllib.request, "build_opener") as build_opener:
            self.assertEqual(
                urls._derive_course_group_name(
                    "https://www.coolenglish.edu.tw/course/view.php?id=713", Manager()
                ),
                "713",
            )
        build_opener.assert_not_called()

    def test_go_accepts_pipe_separated_group_selection(self):
        urls.save_course_groups(
            [
                {"name": "學習", "urls": ["https://example.com/learn"]},
                {"name": "影片", "urls": ["https://example.com/video"]},
            ]
        )
        with patch("builtins.input", return_value="a|b"), patch.object(
            urls, "_run_course_urls"
        ) as run:
            manager = object()
            urls.cmd_go(manager, ["-s"])

        run.assert_called_once()
        self.assertIs(run.call_args.args[0], manager)
        self.assertEqual(
            run.call_args.args[1:],
            (["https://example.com/learn", "https://example.com/video"], True),
        )

    def test_added_links_use_manual_group_name_and_append_to_that_group(self):
        urls.save_course_groups([{"name": "學習", "urls": ["https://example.com/old"]}])
        with patch.object(urls, "_derive_course_group_name", return_value="學習"), patch(
            "builtins.input", side_effect=["1", "https://example.com/new", "學習"]
        ):
            urls.cmd_url(object(), [])

        self.assertEqual(
            urls.load_course_groups(),
            [
                {
                    "name": "學習",
                    "urls": ["https://example.com/old", "https://example.com/new"],
                }
            ],
        )

    def test_name_command_renames_link_groups(self):
        urls.save_course_groups([{"name": "學習", "urls": ["https://example.com/course"]}])
        with patch("builtins.input", side_effect=["2", "1", "進階課程"]):
            cmd_name(object(), [])

        self.assertEqual(
            urls.load_course_groups(),
            [
                {
                    "name": "進階課程",
                    "urls": ["https://example.com/course"],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
