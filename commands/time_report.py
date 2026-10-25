"""Learning-time report command."""
from __future__ import annotations
from .._compat import *
from ..paths import *
from ..colors import *
from ..security import *
from ..accounts import *
from ..ui import *
from html.parser import HTMLParser


class _TimeTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._row: list[str] = []
        self._cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "sort-table":
            self._in_table = True
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_table and self._in_row and tag == "td":
            self._in_cell = True
            self._cell = []
        elif self._in_cell and tag == "br":
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._row:
                self.rows.append(self._row)
            self._in_row = False
        elif tag == "table" and self._in_table:
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)


def _extract_time_rows(html: str) -> list[list[str]]:
    parser = _TimeTableParser()
    parser.feed(html)
    return [row for row in parser.rows if len(row) >= 4]


def _render_time_rows(rows: list[list[str]], url: str, account: str) -> str | None:
    if not rows:
        return None
    import shutil
    import unicodedata

    header = ["學習月份", "停留平台時間", "觀看影片時間", "練習時間"]

    def width(text: str) -> int:
        return sum(
            2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
            for character in text
        )

    table_rows = [header, *rows]
    column_widths = [max(width(row[index]) for row in table_rows) for index in range(4)]
    terminal_width = max(40, shutil.get_terminal_size((100, 24)).columns)
    gap = min(8, max(2, (terminal_width - sum(column_widths) - 4) // 3))

    def pad(text: str, size: int) -> str:
        return text + " " * max(0, size - width(text))

    def center(text: str) -> str:
        return " " * max(0, (terminal_width - width(text)) // 2) + text

    table_width = sum(column_widths) + 3 * gap
    lines = [
        "",
        center(f"┏{'━' * 22}┓"),
        center("┃        學習時間        ┃"),
        center(f"┗{'━' * 22}┛"),
        center(_apply_color("url", url)),
        center(_apply_color("url", f"({account})")),
        "",
        center(_apply_color("header", (" " * gap).join(pad(header[i], column_widths[i]) for i in range(4)))),
        center(_apply_color("sep", "─" * table_width))
    ]
    current_month = datetime.now().strftime("%Y/%m")
    for row in rows:
        cells = (" " * gap).join(pad(row[index], column_widths[index]) for index in range(4))
        if row[0] == current_month:
            match = re.search(r"(\d+)\s*小時", row[1])
            under_threshold = bool(match and int(match.group(1)) < 12)
            label = " ← 當月 未達標" if under_threshold else " ← 當月"
            lines.append(center(_apply_color("cur", f"▶ {cells}{label}")))
        else:
            match = re.search(r"(\d+)\s*小時", row[1])
            if match and int(match.group(1)) < 12:
                lines.append(center(_apply_color("low", f"  {cells}  未達標")))
            else:
                lines.append(center(f"  {cells}"))
    lines.append(center(_apply_color("sep", "─" * table_width)))
    return "\n".join(lines)


def cmd_time(mgr: AccountManager, args: list[str]):
    if not mgr.list_accounts():
        status_line("檢查登入狀態", "FAILED")
        note("ERR", "尚未登入，請先執行： cool -l")
        return

    want_raw = "--raw" in args
    args = [a for a in args if a != "--raw"]
    if args:
        note("WARN", "cool -t 不接受帳號參數，請直接使用 cool -t 並從選單選擇帳號")
        return

    url = DEFAULT_TARGET
    account_id = None

    if len(mgr.list_accounts()) == 1:
        account_id = mgr.list_accounts()[0]["name"]
        note("INFO", f"僅一個帳號，自動使用：{account_id}")
    else:
        note("INFO", "請選擇要用哪個帳號的 cookie 查詢時數")
        chosen = _choose_account_interactive(mgr, "請選擇要用哪個帳號查詢時數")
        if not chosen:
            return
        account_id = chosen["name"]

    cookie_path = mgr.get_cookie_path(account_id)
    if cookie_path is None:
        status_line("檢查帳號", "FAILED")
        note("ERR", f"找不到帳號: {account_id}，請用 -s 查看")
        return
    if not cookie_path.exists():
        status_line("檢查 cookie", "FAILED")
        note("ERR", f"cookie 檔案不存在: {cookie_path}，請重新 -l 登入")
        return

    acc = mgr.get_account_for_cookie(cookie_path)
    acc_label = f"{acc['name']} ({acc['email']})" if acc else str(cookie_path)
    note("INFO", f"使用帳號：{acc_label}")

    import urllib.request
    import re

    status_line("連線中", "WORK")

    def _build_cookie_header(path: Path) -> str:
        try:
            txt = path.read_text(encoding="utf-8")
        except Exception as e:
            note("ERR", f"讀取 cookie 失敗：{e}")
            return ""
        parts = []
        for line in txt.splitlines():
            normalized = line[len("#HttpOnly_") :] if line.startswith("#HttpOnly_") else line
            if not normalized or (normalized.startswith("#") and not line.startswith("#HttpOnly_")):
                continue
            segs = normalized.split("\t")
            if len(segs) >= 7:
                parts.append(f"{segs[5]}={segs[6]}")
        return "; ".join(parts)

    cookie_header = _build_cookie_header(cookie_path)
    if not cookie_header:
        status_line("連線中", "FAILED")
        note("ERR", f"cookie 檔案為空或格式錯誤：{cookie_path}")
        return

    status_line("檢查 cookie", "WORK")
    def _check_cookie_local(p: Path):
        try:
            txt = p.read_text(encoding="utf-8")
            has_moodle = False
            moodle_valid = False
            now_ts = datetime.now().timestamp()
            for raw_line in txt.splitlines():
                line = raw_line[len("#HttpOnly_") :] if raw_line.startswith("#HttpOnly_") else raw_line
                if not line or (line.startswith("#") and not raw_line.startswith("#HttpOnly_")):
                    continue
                segs = line.split("\t")
                if len(segs) < 7:
                    continue
                name = segs[5]
                exp_s = segs[4]
                try:
                    exp = int(exp_s)
                except Exception:
                    exp = 0
                if name == "MoodleSession":
                    has_moodle = True
                    if exp == 0 or exp > now_ts:
                        moodle_valid = True
                    else:
                        return False, f"MoodleSession 已過期 (exp={exp} < now)"
            if not has_moodle:
                return False, "缺少 MoodleSession（可能從未登入或檔案損毀）"
            if not moodle_valid:
                return False, "無有效的 MoodleSession"
            try:
                age = now_ts - p.stat().st_mtime
                if age > 14*86400:
                    note("WARN", f"cookie 已 {int(age/86400)} 天未更新，建議重新登入")
            except Exception:
                pass
            return True, "OK"
        except Exception as e:
            return False, f"讀取失敗：{e}"

    ok, reason = _check_cookie_local(cookie_path)
    if not ok:
        status_line("檢查 cookie", "FAILED")
        note("WARN", f"帳號 {acc_label} 的 cookie 無效：{reason}，請重新 cool -l 登入")
        return

    stored_uid = acc.get("user_id") if acc else None
    if stored_uid and stored_uid not in ("0", "1"):
        url = f"{BASE_URL}/time/time_view_detail_by_people.php?id={stored_uid}"
        note("INFO", f"使用已儲存的 userId：{stored_uid}")
        note("INFO", f"目標網址：{url}")
        _use_stored = True
    else:
        _use_stored = False

    if not _use_stored:
        def _detect_time_url(cookie_hdr: str):
            probe_urls = [
                f"{BASE_URL}/user/profile.php",
                f"{BASE_URL}/time/time_view_report.php",
                f"{BASE_URL}/my/",
            ]
            expired_count = 0
            for probe in probe_urls:
                try:
                    req_p = urllib.request.Request(probe, headers={"User-Agent": UA, "Cookie": cookie_hdr, "Referer": BASE_URL + "/"})
                    opener_p = urllib.request.build_opener()
                    with opener_p.open(req_p, timeout=10) as resp:
                        html_p = resp.read().decode("utf-8", errors="replace")
                    is_login = "logintoken" in html_p and "登入" in html_p[:3000]
                    if is_login:
                        expired_count += 1
                        continue
                    m = re.search(r'time_view_detail_by_people\.php\?id=(\d+)', html_p)
                    if m:
                        return f"{BASE_URL}/time/time_view_detail_by_people.php?id={m.group(1)}", "ok"
                    m2 = re.search(r'"userId"\s*:\s*(\d+)', html_p)
                    if m2 and m2.group(1) not in ("0", "1"):
                        return f"{BASE_URL}/time/time_view_detail_by_people.php?id={m2.group(1)}", "ok"
                    m3 = re.search(r'user/profile\.php\?id=(\d+)', html_p)
                    if m3 and m3.group(1) not in ("0", "1"):
                        return f"{BASE_URL}/time/time_view_detail_by_people.php?id={m3.group(1)}", "ok"
                except Exception:
                    continue
            if expired_count == len(probe_urls):
                return None, "expired"
            return None, "not_found"

        detected_url, reason = _detect_time_url(cookie_header)
        if reason == "expired":
            status_line("連線中", "FAILED")
            note("WARN", f"帳號 {acc_label} 的 session 可能已過期，請重新 cool -l 登入")
            note("INFO", "已停止訪問，避免用他人 id 存取")
            return
        if detected_url:
            url = detected_url
            note("INFO", f"已解析個人時數頁：{url}")
        else:
            url = f"{BASE_URL}/time/time_view_report.php"
            note("WARN", "無法自動解析個人 id，改用通用時數總覽頁（若無資料請確認帳號權限）")
        note("INFO", f"目標網址：{url}")

    try:
        probe_req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": cookie_header, "Referer": BASE_URL + "/"})
        opener_probe = urllib.request.build_opener()
        with opener_probe.open(probe_req, timeout=20) as resp:
            final_url = resp.geturl()
            html_probe = resp.read().decode("utf-8", errors="replace")
        if "login" in final_url.lower() or "logintoken" in html_probe or "loginredirect" in final_url:
            status_line("檢查 cookie", "FAILED")
            note("WARN", f"帳號 {acc_label} 的 session 已過期（探測到 {final_url}），請重新 cool -l 登入")
            return
    except Exception as e:
        try:
            from urllib.error import HTTPError
            if isinstance(e, HTTPError) and e.code in (301, 302, 303, 307, 308):
                loc = ""
                try:
                    loc = e.headers.get("Location", "") if e.headers else ""
                except Exception:
                    loc = ""
                url_str = getattr(e, "url", "") or loc or str(e)
                if "login" in loc.lower() or "login" in url_str.lower() or "loginredirect" in loc.lower():
                    status_line("檢查 cookie", "FAILED")
                    note("WARN", f"帳號 {acc_label} 的 session 已過期（303 導向 {loc or url_str}），請重新 cool -l 登入")
                    return
                if e.code == 303:
                    status_line("檢查 cookie", "FAILED")
                    note("WARN", f"帳號 {acc_label} 的 session 已過期（HTTP 303），請重新 cool -l 登入")
                    return
        except Exception:
            pass
        status_line("取得學習時數 HTML", "FAILED")
        note("ERR", f"無法使用已儲存的 Cookie 取得時數頁面：{e}")
        return
    status_line("檢查 cookie", "OK")

    html = html_probe
    if "logintoken" in html and "登入" in html[:2000]:
        status_line("檢查 cookie", "FAILED")
        note("WARN", f"帳號 {acc_label} 的 session 可能已過期，請重新 cool -l 登入")
        return
    status_line("取得學習時數 HTML", "OK")
    rendered_text = (
        html if want_raw else _render_time_rows(_extract_time_rows(html), final_url, acc_label)
    )
    if rendered_text is None:
        status_line("解析學習時數", "FAILED")
        note("ERR", "已使用 Cookie 取得網頁，但其中找不到時數資料表；網站頁面格式可能已更新。")
        return

    if want_raw:
        print("----------------------------------------")
        print(html)
        return

    if rendered_text and rendered_text.strip():
        sys.stdout.write(rendered_text.strip("\n") + "\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(html if html.endswith("\n") else html + "\n")
        sys.stdout.flush()

__all__ = [name for name in globals() if not name.startswith("__")]
