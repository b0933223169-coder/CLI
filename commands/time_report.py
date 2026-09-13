"""Learning-time report command."""
from __future__ import annotations
from .._compat import *
from ..paths import *
from ..colors import *
from ..security import *
from ..accounts import *
from ..ui import *
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
    import ssl

    status_line("連線中", "WORK")

    def _build_cookie_header(path: Path) -> str:
        try:
            txt = path.read_text(encoding="utf-8")
        except Exception as e:
            note("ERR", f"讀取 cookie 失敗：{e}")
            return ""
        parts = []
        for line in txt.splitlines():
            if not line or line.startswith("#"):
                continue
            segs = line.split("\t")
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
            for line in txt.splitlines():
                if not line or line.startswith("#"):
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
                    ctx = ssl._create_unverified_context()
                    opener_p = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
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
        ctx_probe = ssl._create_unverified_context()
        opener_probe = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx_probe))
        with opener_probe.open(probe_req, timeout=5) as resp:
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
        note("INFO", f"cookie 輕量探測失敗（將續嘗試完整載入）：{e}")
    status_line("檢查 cookie", "OK")

    def _fetch_with_url(req_, timeout=15):
        try:
            ctx = ssl._create_unverified_context()
            opener_ = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            with opener_.open(req_, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace"), False
        except Exception as e:
            msg = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in msg or "SSL" in msg:
                raise
            raise

    html = None
    rendered_text = None
    use_playwright = True

    if use_playwright and not want_raw:
        try:
            from playwright.sync_api import sync_playwright
            pw_cookies = []
            try:
                txt = cookie_path.read_text(encoding="utf-8")
                for line in txt.splitlines():
                    if not line or line.startswith("#"):
                        continue
                    segs = line.split("\t")
                    if len(segs) >= 7:
                        domain, flag, path_, secure, expiry, name, value = segs[:7]
                        try:
                            exp = int(expiry)
                        except Exception:
                            exp = -1
                        if exp == 0:
                            exp = -1
                        pw_cookies.append({
                            "name": name, "value": value,
                            "domain": domain.lstrip("."), "path": path_,
                            "secure": secure == "TRUE", "httpOnly": False,
                            "expires": exp, "sameSite": "Lax",
                        })
            except Exception as ce:
                note("WARN", f"解析 cookie 供 Playwright 使用失敗：{ce}")
                pw_cookies = []

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=UA)
                if pw_cookies:
                    try:
                        ctx.add_cookies(pw_cookies)
                    except Exception as ce:
                        note("WARN", f"注入 cookie 失敗：{ce}")
                page = ctx.new_page()
                status_line("載入頁面 (Playwright)", "WORK")
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(1500)
                try:
                    if "login" in page.url or "登入" in page.title():
                        html_tmp = page.content()[:3000]
                        if "logintoken" in html_tmp:
                            note("WARN", f"帳號 {acc_label} 的 session 已過期，導向至登入頁，請重新 cool -l 登入")
                            status_line("載入頁面 (Playwright)", "FAILED")
                            browser.close()
                            return
                except Exception:
                    pass
                try:
                    page.wait_for_selector("table#sort-table", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(1800)
                def _extract_table():
                    try:
                        return page.evaluate("""() => {
                            const rows = Array.from(document.querySelectorAll('#sort-table tbody tr'));
                            return rows.map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()));
                        }""")
                    except Exception:
                        return []
                all_rows = _extract_table()
                for _ in range(5):
                    nxt = page.locator("div.next")
                    if nxt.count() == 0 or not nxt.first.is_visible():
                        break
                    cls = nxt.first.get_attribute("class") or ""
                    if "disabled" in cls:
                        break
                    seen = {r[0] for r in all_rows if r}
                    try:
                        nxt.first.click()
                        page.wait_for_timeout(1800)
                        try:
                            page.wait_for_selector("table#sort-table tbody tr", timeout=8000)
                        except Exception:
                            pass
                        page.wait_for_timeout(800)
                        new_rows = _extract_table()
                        if not new_rows:
                            break
                        added = [r for r in new_rows if r and r[0] not in seen]
                        if not added:
                            break
                        all_rows.extend(added)
                    except Exception:
                        break
                try:
                    if "login" in page.url or "登入" in page.title():
                        note("WARN", f"帳號 {acc_label} 的 session 已過期（導向至 {page.url}），請重新 cool -l 登入")
                        status_line("載入頁面 (Playwright)", "FAILED")
                        browser.close()
                        return
                except Exception:
                    pass
                if not all_rows:
                    note("WARN", f"帳號 {acc_label} 的時數資料為空（可能 session 已過期或無權限），請重新 cool -l 登入")
                    status_line("載入頁面 (Playwright)", "FAILED")
                    browser.close()
                    return
                from datetime import datetime as _dt
                cur_month = _dt.now().strftime("%Y/%m")
                header = ["學習月份", "停留平台時間", "觀看影片時間", "練習時間"]
                def _w(s):
                    import unicodedata
                    return sum(2 if unicodedata.east_asian_width(ch) in ("W","F") else 1 for ch in s)
                cols = [header] + all_rows
                cols = [r for r in cols if len(r) >= 4]
                if cols:
                    import shutil
                    term_w = shutil.get_terminal_size((100, 24)).columns
                    if term_w < 40:
                        term_w = 100
                    widths = [max(_w(r[i]) for r in cols) for i in range(4)]
                    base_gap = 2
                    need = sum(widths) + base_gap*3 + 4
                    extra = max(0, term_w - need)
                    gap = base_gap + extra // 3
                    gap = min(gap, 8)
                    def _pad(s, w):
                        return s + " " * max(0, w - _w(s))
                    lines = []
                    try:
                        _page_title = page.title().split(" |")[0].strip()
                        if not _page_title or "學習時間" not in _page_title:
                            _h = page.locator("h1, h2, text=學習時間").first.inner_text(timeout=2000)
                            if _h:
                                _page_title = _h.strip().split("\n")[0]
                    except Exception:
                        _page_title = "學習時間"
                    import re as _re_ansi
                    _ansi_re = _re_ansi.compile(r'\x1b\[[0-9;]*m')
                    def _center(s: str) -> str:
                        plain = _ansi_re.sub('', s)
                        pw = _w(plain)
                        pad = max(0, (term_w - pw) // 2)
                        return " " * pad + s
                    BOLD = "\033[1m"
                    pad_w = display_width(_page_title)
                    border = "━" * (pad_w + 6)
                    _title_c = get_color("title")
                    top = f"{BOLD}{_title_c}┏{border}┓{RESET}"
                    bot = f"{BOLD}{_title_c}┗{border}┛{RESET}"
                    _title_text_c = get_color("title_text")
                    _title_c2 = get_color("title")
                    mid = f"{BOLD}{_title_c2}┃   {BOLD}{_title_text_c}{_page_title}{RESET}{BOLD}{_title_c2}   ┃{RESET}"
                    lines.append("")
                    lines.append(_center(top))
                    lines.append(_center(mid))
                    lines.append(_center(bot))
                    lines.append(_center(_apply_color("url", page.url)))
                    lines.append(_center(_apply_color("url", f"({acc_label})")))
                    lines.append("")
                    TAG_W = _w(" ← 當月 未達標")
                    header_line = (" " * gap).join(_pad(header[i], widths[i]) for i in range(4))
                    header_full = f"  {header_line}  {' ' * TAG_W}"
                    lines.append(_center(_apply_color("header", header_full)))
                    sep_len = min(term_w - 2, sum(widths) + gap*3 + 2 + 2 + TAG_W)
                    lines.append(_center(_apply_color("sep", '-'* sep_len)))
                    import re as _re2
                    for r in all_rows:
                        if len(r) < 4:
                            continue
                        is_cur = r[0] == cur_month
                        m_h = _re2.search(r'(\d+)\s*小時', r[1])
                        hours = int(m_h.group(1)) if m_h else 999
                        is_low = hours < 12
                        row_cells = [ _pad(r[i], widths[i]) for i in range(4) ]
                        core = (" " * gap).join(row_cells)
                        if is_cur:
                            tag_plain = " ← 當月 未達標" if is_low else "  ← 當月"
                            tag_padded = tag_plain + " " * (TAG_W - _w(tag_plain))
                            prefix = "▶ "
                            full = f"{prefix}{core}  {tag_padded}"
                            full = _apply_color("cur", full)
                        elif is_low:
                            tag_plain = "  未達標"
                            tag_padded = tag_plain + " " * (TAG_W - _w(tag_plain))
                            full = f"  {core}  {tag_padded}"
                            full = _apply_color("low", full)
                        else:
                            tag_plain = ""
                            tag_padded = " " * TAG_W
                            full = f"  {core}  {tag_padded}"
                            lines.append(_center(full))
                            continue
                        lines.append(_center(full))
                    lines.append(_center(f"{get_color('sep')}{'─'* sep_len}{RESET}"))
                    rendered_text = "\n".join(lines)
                else:
                    rendered_text = None
                html = page.content()
                browser.close()
                status_line("載入頁面 (Playwright)", "OK")
        except Exception as e:
            note("WARN", f"Playwright 渲染失敗，退回 urllib 模式：{e}")
            html = None

    if html is None:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": cookie_header})
        try:
            html, insecure = _fetch_with_url(req, timeout=15)
            if insecure:
                note("NOTICE", "已使用不驗證憑證模式取得資料")
        except Exception as e:
            status_line("連線中", "FAILED")
            note("ERR", f"請求失敗：{e}")
            return
        status_line("連線中", "OK")

        if "logintoken" in html and "登入" in html[:2000]:
            note("WARN", f"帳號 {acc_label} 的 session 可能已過期，請重新 cool -l 登入")
            return
        if not want_raw:
            rendered_text = None
            import shutil, subprocess
            if shutil.which("w3m"):
                try:
                    proc = subprocess.run(
                        ["w3m", "-T", "text/html", "-dump", "-cols", "100"],
                        input=html.encode("utf-8"), capture_output=True, timeout=10
                    )
                    if proc.returncode == 0:
                        rendered_text = proc.stdout.decode("utf-8", errors="replace")
                except Exception:
                    pass
            if rendered_text is None and shutil.which("lynx"):
                try:
                    proc = subprocess.run(
                        ["lynx", "-stdin", "-dump", "-nolist"],
                        input=html.encode("utf-8"), capture_output=True, timeout=10
                    )
                    if proc.returncode == 0:
                        rendered_text = proc.stdout.decode("utf-8", errors="replace")
                except Exception:
                    pass
            if rendered_text is None:
                try:
                    import re as _re
                    tmp = _re.sub(r'<script.*?</script>', '', html, flags=_re.S|_re.I)
                    tmp = _re.sub(r'<style.*?</style>', '', tmp, flags=_re.S|_re.I)
                    tmp = _re.sub(r'<[^>]+>', '\n', tmp)
                    tmp = _re.sub(r'\n{3,}', '\n\n', tmp)
                    rendered_text = tmp.strip()
                except Exception:
                    rendered_text = html
        else:
            rendered_text = html

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
