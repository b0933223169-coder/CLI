"""Saved-course URL management and browser command."""
from __future__ import annotations
from .._compat import *
from ..paths import *
from ..colors import *
from ..security import *
from ..accounts import *
from ..ui import *
from ..playwright_log import attach_context_logging, launch_browser
from ..modifiers import get_current as _current_mods, format_duration
import html
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

def _norm_url(url: str) -> str:
    """比對重複用：忽略 #片段、結尾斜線，以及協定／主機的大小寫。"""
    try:
        parts = urllib.parse.urlsplit(url.strip())
        path = parts.path.rstrip("/")
        return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))
    except ValueError:
        return url.strip()

def _is_windows_tty() -> bool:
    return os.name == "nt" and sys.stdin.isatty() and sys.stdout.isatty()

def _read_paste(prompt: str) -> str:
    """讀取使用者貼上的內容；多行貼上時把剩餘行一併收進來，避免溢出到 cool> 變成未知指令。"""
    first = input(prompt)
    if not _is_windows_tty():
        return first
    import msvcrt
    time.sleep(0.25)
    buf, quiet = [], 0
    while quiet < 8:                      # 連續約 0.4 秒沒有新輸入才結束
        if msvcrt.kbhit():
            quiet = 0
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            buf.append("\n" if ch in ("\r", "\n") else ch)
        else:
            time.sleep(0.05)
            quiet += 1
    return first + "\n" + "".join(buf)

def _windows_multiselect(options: list[str], title: str):
    """上下鍵移動、空白鍵勾選／取消、Enter 確認、a 全選／全不選、Esc 取消。回傳已勾選的索引清單，取消回傳 None。"""
    import msvcrt
    checked: set[int] = set()
    current = 0
    while True:
        os.system("cls")
        print(title)
        print("─" * 52)
        for index, option in enumerate(options):
            marker = ">" if index == current else " "
            box = "[x]" if index in checked else "[ ]"
            print(f"{marker} {box} {option}")
        print()
        print(f"已選 {len(checked)} 項    ↑↓ 移動  空白 選取/取消  a 全選  Enter 確認  Esc 返回", flush=True)
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H" and current > 0:
                current -= 1
            elif key == "P" and current < len(options) - 1:
                current += 1
        elif key == " ":
            checked.symmetric_difference_update({current})
        elif key in ("a", "A"):
            checked = set() if len(checked) == len(options) else set(range(len(options)))
        elif key in ("\r", "\n"):
            if not checked:
                checked.add(current)         # 沒勾選就 Enter：視為只選目前這一項
            return sorted(checked)
        elif key == "\x1b":
            return None

def _windows_category_picker(cats: "dict[str, list[str]]", title: str):
    """第一層只列分類：空白鍵選取整個分類、Tab 進入分類挑選個別連結、Enter 確認、Esc 取消。
    回傳要刪除的網址集合；取消回傳 None。"""
    import msvcrt
    names = list(cats)
    whole: set[str] = set()                       # 整個分類
    partial: dict[str, set[str]] = {n: set() for n in names}   # 分類內個別連結
    cur = 0

    def read_key():
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        return {" ": "space", "\t": "tab", "\r": "enter", "\n": "enter", "\x1b": "esc"}.get(key, key.lower())

    def enter_category(name: str):
        urls = cats[name]
        pos = 0
        while True:
            os.system("cls")
            print(f"{title}\n分類「{name}」（{len(urls)} 個連結）")
            print("─" * 52)
            for i, url in enumerate(urls):
                on = name in whole or url in partial[name]
                print(f"{'>' if i == pos else ' '} {'[x]' if on else '[ ]'} {url}")
            print()
            print("↑↓ 移動  空白 選取/取消  a 全選  Tab/Enter/Esc 返回分類清單", flush=True)
            k = read_key()
            if k == "up" and pos > 0:
                pos -= 1
            elif k == "down" and pos < len(urls) - 1:
                pos += 1
            elif k == "space":
                if name in whole:                 # 整類已選 → 展開成個別連結，再取消這一個
                    whole.discard(name)
                    partial[name] = set(urls)
                partial[name].symmetric_difference_update({urls[pos]})
            elif k == "a":
                if name in whole or len(partial[name]) == len(urls):
                    whole.discard(name)
                    partial[name] = set()
                else:
                    partial[name] = set(urls)
            elif k in ("tab", "enter", "esc"):
                break
        if len(partial[name]) == len(urls):       # 全部勾滿 = 整類
            whole.add(name)
            partial[name] = set()

    while True:
        os.system("cls")
        print(title)
        print("─" * 52)
        for i, name in enumerate(names):
            if name in whole:
                tag = "[x]"
                extra = ""
            elif partial[name]:
                tag = "[-]"
                extra = f"  已選 {len(partial[name])} 個"
            else:
                tag = "[ ]"
                extra = ""
            print(f"{'>' if i == cur else ' '} {tag} 分類「{name}」（{len(cats[name])} 個連結）{extra}")
        print()
        print("↑↓ 移動  空白 選取整個分類  Tab 進入分類選連結  Enter 確認刪除  Esc 返回", flush=True)
        k = read_key()
        if k == "up" and cur > 0:
            cur -= 1
        elif k == "down" and cur < len(names) - 1:
            cur += 1
        elif k == "space":
            n = names[cur]
            if n in whole:
                whole.discard(n)
            else:
                whole.add(n)
                partial[n] = set()
        elif k == "tab":
            enter_category(names[cur])
        elif k == "enter":
            doomed = {u for n in whole for u in cats[n]} | {u for n in names for u in partial[n]}
            if not doomed:                        # 什麼都沒選 → 視為選取目前這個分類
                doomed = set(cats[names[cur]])
            return doomed
        elif k == "esc":
            return None

def _arrow_pick(options: list[str], title: str):
    """上下鍵選單（與 cool -a 相同）；非 Windows 終端回傳 None 讓呼叫端改用編號輸入。"""
    if not _is_windows_tty():
        return None
    return _windows_select(options, title)

def load_course_groups() -> list[dict[str, object]]:
    """Load grouped course URLs while accepting legacy flat urls.txt files."""
    if not URLS_FILE.exists():
        return []
    try:
        content = URLS_FILE.read_text(encoding="utf-8")
    except OSError as error:
        note("ERR", f"讀取課程網址失敗：{error}")
        return []
    groups: dict[tuple[str, str], list[str]] = {}
    current_group = "未分類"
    current_category = "未分類"
    explicit_categories: set[tuple[str, str]] = set()
    for line in content.splitlines():
        stripped = line.strip()
        match = re.match(r"^#\s*group:\s*(.*)$", stripped, re.IGNORECASE)
        if match:
            try:
                current_group = urllib.parse.unquote(match.group(1)) or "未分類"
            except Exception:
                current_group = match.group(1) or "未分類"
            current_category = current_group
            groups.setdefault((current_category, current_group), [])
            continue
        category_match = re.match(r"^#\s*category:\s*(.*)$", stripped, re.IGNORECASE)
        if category_match:
            try:
                current_category = urllib.parse.unquote(category_match.group(1)) or "未分類"
            except Exception:
                current_category = category_match.group(1) or "未分類"
            groups.setdefault((current_category, current_group), [])
            explicit_categories.add((current_category, current_group))
            continue
        if not re.match(r"^https?://", stripped, re.IGNORECASE):
            continue
        try:
            parsed = urllib.parse.urlsplit(stripped)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        urls = groups.setdefault((current_category, current_group), [])
        if stripped not in urls:
            urls.append(stripped)
    result = []
    for (category, name), urls in groups.items():
        if not urls:
            continue
        group = {"name": name, "urls": urls}
        if (category, name) in explicit_categories:
            group["category"] = category
        result.append(group)
    return result

def load_urls() -> list[str]:
    """Read and flatten all saved course URLs."""
    return [url for group in load_course_groups() for url in group["urls"]]

def save_course_groups(groups: list[dict[str, object]]) -> None:
    header = [
        "# Cool English 課程網址清單",
        f"# 最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# 群組以 # group: 名稱 標示；網址可供 cool -g 選擇",
        "",
    ]
    lines = list(header)
    seen: set[str] = set()
    for group in groups:
        name = str(group.get("name") or "未分類").strip() or "未分類"
        urls = group.get("urls", [])
        if not isinstance(urls, list):
            continue
        unique_urls = [url for url in urls if isinstance(url, str) and url not in seen]
        if not unique_urls:
            continue
        lines.append(f"# group: {urllib.parse.quote(name, safe='')}")
        if "category" in group:
            category = str(group.get("category") or name).strip() or name
            lines.append(f"# category: {urllib.parse.quote(category, safe='')}")
        lines.extend(unique_urls)
        lines.append("")
        seen.update(unique_urls)
    data = "\n".join(lines) + "\n"
    _atomic_write(URLS_FILE, data, 0o600)

def save_urls(urls: list[str]) -> None:
    """Write a legacy flat URL list as the default group."""
    save_course_groups([{"name": "未分類", "urls": urls}])

def cmd_write(args: list[str] = None):
    """批量寫入/貼上課程網址並自動排版儲存。"""
    print(f"{CYAN}=== 批量寫入課程網址 (-w) ==={RESET}")
    print(f"{DIM}請直接貼上包含網址的文字（可多行、可含雜訊）。{RESET}")
    print(f"{DIM}輸入完成後請按兩次 Enter，或輸入空白行送出：{RESET}\n")

    input_lines = []
    while True:
        try:
            line = input()
            if not line.strip():
                if input_lines:
                    break
                else:
                    continue
            input_lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print()
            break

    raw_text = "\n".join(input_lines)
    found_urls = re.findall(r'https?://[^\s"\'<>]+', raw_text)
    if not found_urls:
        note("WARN", "未在輸入內容中找到任何有效網址 (http/https)")
        return []

    cleaned_urls = []
    for u in found_urls:
        u = u.rstrip(".,;)>]")
        if u not in cleaned_urls:
            cleaned_urls.append(u)

    _add_course_urls(AccountManager(), cleaned_urls)
    return load_urls()

def _choose_url_interactive(urls: list[str]) -> list[str] | str | None:
    """提供互動式清單選擇要訪問的網址。"""
    if not urls:
        return None
    if os.name == "nt":
        print(f"\n{CYAN}已儲存的課程網址清單：{RESET}")
        for i, u in enumerate(urls, 1):
            print(f"  {YELLOW}{i:2d}.{RESET} {u}")
        print(f"  {GREEN}A.{RESET} 同時開啟全部")
        try:
            choice = input("請選擇編號/A（直接 Enter 取消）: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not choice:
            return None
        if choice.upper() == "A":
            return "ALL"
        try:
            index = int(choice) - 1
            return urls[index] if 0 <= index < len(urls) else None
        except ValueError:
            return None
    try:
        import curses
        selected_res = None
        action = "select"

        def _curses_url_menu(stdscr):
            nonlocal selected_res, action
            curses.curs_set(0)
            stdscr.keypad(True)
            stdscr.nodelay(False)
            cur = 0
            confirm_delete = False
            total_items = len(urls) + 1
            marked_set = set()

            while True:
                stdscr.clear()
                h, w = stdscr.getmaxyx()
                stdscr.addstr(0, 0, "課程網址選單 [1-9/Space 多選] [Del 刪除]"[:w-1])
                stdscr.addstr(1, 0, DIM + "─" * min(w - 1, 80) + RESET)

                for i, u in enumerate(urls):
                    y = 3 + i
                    if y >= h - 3:
                        break
                    mark = "[✓]" if i in marked_set else "[ ]"
                    label = f" {mark} [{i+1:2d}] {u} "
                    if i == cur:
                        stdscr.addstr(y, 2, label[:w-4], curses.A_REVERSE | curses.A_BOLD)
                    else:
                        stdscr.addstr(y, 2, label[:w-4])

                all_y = 3 + len(urls)
                if all_y < h - 3:
                    all_label = "     [ A] ★ 同時開啟全部已儲存網址 (全開模式) "
                    if cur == len(urls):
                        stdscr.addstr(all_y, 2, all_label[:w-4], curses.A_REVERSE | curses.A_BOLD)
                    else:
                        stdscr.addstr(all_y, 2, all_label[:w-4], curses.A_BOLD)

                hint_y = min(h - 2, 3 + total_items + 1)
                if confirm_delete and cur < len(urls):
                    warn_msg = f" ⚠️ 確定要從清單中刪除第 [{cur+1}] 個網址嗎？ 按 [y] 確認刪除，其他鍵取消 "
                    stdscr.addstr(hint_y, 0, warn_msg[:w-1], curses.A_REVERSE | curses.A_BOLD)
                else:
                    count_str = f"已勾選 {len(marked_set)} 個網址" if marked_set else "單網址模式"
                    stdscr.addstr(hint_y, 0, DIM + f"[{count_str}] 1-9/Space:多選 | Del:刪除 | Enter:開啟"[:w-1] + RESET)

                stdscr.refresh()
                key = stdscr.getch()

                if confirm_delete:
                    if key in (ord('y'), ord('Y')):
                        action = "delete"
                        selected_res = cur
                        break
                    else:
                        confirm_delete = False
                    continue

                if key == 27:
                    selected_res = None
                    break

                if key == curses.KEY_UP and cur > 0:
                    cur -= 1
                elif key == curses.KEY_DOWN and cur < total_items - 1:
                    cur += 1
                elif ord('1') <= key <= ord('9'):
                    target = key - ord('1')
                    if target < len(urls):
                        cur = target
                        if target in marked_set:
                            marked_set.remove(target)
                        else:
                            marked_set.add(target)
                elif key == ord(' '):
                    if cur < len(urls):
                        if cur in marked_set:
                            marked_set.remove(cur)
                        else:
                            marked_set.add(cur)
                elif key in (ord('a'), ord('A')):
                    selected_res = "ALL"
                    action = "select"
                    break
                elif key in (curses.KEY_DC, ord('d'), ord('D'), 330, 127):
                    if cur < len(urls):
                        confirm_delete = True
                elif key in (10, 13, curses.KEY_ENTER):
                    if cur == len(urls):
                        selected_res = "ALL"
                    elif marked_set:
                        selected_res = [urls[i] for i in sorted(marked_set)]
                    else:
                        selected_res = urls[cur]
                    action = "select"
                    break
                elif key in (ord('q'), ord('Q')):
                    selected_res = None
                    break

        curses.wrapper(_curses_url_menu)
        if selected_res is None:
            note("INFO", "已取消選擇")
            return None

        if action == "delete":
            del_idx = selected_res
            deleted_url = urls.pop(del_idx)
            save_urls(urls)
            status_line("刪除網址", "DONE")
            note("INFO", f"已從 urls.txt 移除網址：{deleted_url}")
            return None

        return selected_res
    except Exception as e:
        note("WARN", f"curses 選單失敗 ({e})，改用數字選單")
        print(f"\n{CYAN}已儲存的課程網址清單：{RESET}")
        for i, u in enumerate(urls, 1):
            print(f"  {YELLOW}{i:2d}.{RESET} {u}")
        print(f"  {GREEN} A.{RESET} {BOLD}同時開啟全部 (多分頁並行模式){RESET}")
        try:
            choice = input("\n請選擇編號 (1~N / A 全部 / 直接 Enter 取消): ").strip()
            if not choice:
                return None
            if choice.upper() == "A":
                return "ALL"
            idx = int(choice) - 1
            if 0 <= idx < len(urls):
                return urls[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        note("INFO", "已取消選擇")
        return None

# Playwright context 只保留使用者可見功能必需的選項（介面語言與時區）。
_CONTEXT_OPTS = dict(
    locale="zh-TW",
    timezone_id="Asia/Taipei",
)

# ─────────────────────────────────────────────────────────────────────────────

class _PageTitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.parts.append(data)

class _CoolEnglishRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        parsed = urllib.parse.urlsplit(new_url)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or (host != "coolenglish.edu.tw" and not host.endswith(".coolenglish.edu.tw"))
        ):
            return None
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)

def _cookie_header_for_url(mgr: "AccountManager", url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host != "coolenglish.edu.tw" and not host.endswith(".coolenglish.edu.tw"):
        return ""
    accounts = mgr.list_accounts()
    if not accounts:
        return ""
    account = accounts[0] if len(accounts) == 1 else _choose_account_interactive(mgr, "選擇用來辨識課程的帳號")
    if not account:
        return ""
    cookie_path = mgr.get_cookie_path(account["name"])
    if not cookie_path or not cookie_path.is_file():
        return ""
    pairs = []
    has_live_session = False
    now = datetime.now().timestamp()
    for line in cookie_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 7:
            domain, _, _, _, expiry_text, name, value = fields[:7]
            domain = domain.lstrip(".").lower()
            if host == domain or host.endswith("." + domain):
                pairs.append(f"{name}={value}")
                try:
                    expiry = int(expiry_text)
                except ValueError:
                    expiry = 0
                if (
                    name == "MoodleSession"
                    and value
                    and (expiry <= 0 or expiry > now)
                    and (domain == "coolenglish.edu.tw" or domain.endswith(".coolenglish.edu.tw"))
                ):
                    has_live_session = True
    if not has_live_session:
        return ""
    return "; ".join(pairs)

def _derive_course_group_name(url: str, mgr: "AccountManager") -> str:
    parsed_url = urllib.parse.urlsplit(url)
    if parsed_url.hostname and (
        parsed_url.hostname == "coolenglish.edu.tw"
        or parsed_url.hostname.endswith(".coolenglish.edu.tw")
    ):
        try:
            cookie_header = _cookie_header_for_url(mgr, url)
            if cookie_header:
                headers = {"User-Agent": UA, "Cookie": cookie_header}
                opener = urllib.request.build_opener(_CoolEnglishRedirectHandler())
                dashboard = urllib.request.Request(f"{BASE_URL}/my/", headers=headers)
                with opener.open(dashboard, timeout=8) as response:
                    dashboard_url = urllib.parse.urlsplit(response.geturl())
                    dashboard_html = response.read(500_000).decode("utf-8", errors="replace")
                user_id_match = re.search(r'"userId"\s*:\s*(\d+)', dashboard_html)
                has_real_user_id = bool(user_id_match and int(user_id_match.group(1)) > 1)
                is_authenticated = (
                    dashboard_url.hostname in ("www.coolenglish.edu.tw", "coolenglish.edu.tw")
                    and "login" not in dashboard_url.path.lower()
                    and not re.search(r"logintoken|type=[\"']password", dashboard_html, re.IGNORECASE)
                    and (
                        has_real_user_id
                        or bool(re.search(r"logout\.php|登出", dashboard_html, re.IGNORECASE))
                    )
                )
                if is_authenticated:
                    request = urllib.request.Request(url, headers=headers)
                    with opener.open(request, timeout=8) as response:
                        final_url = urllib.parse.urlsplit(response.geturl())
                        if (
                            final_url.hostname in ("www.coolenglish.edu.tw", "coolenglish.edu.tw")
                            and "login" not in final_url.path.lower()
                        ):
                            source = response.read(1_000_000).decode("utf-8", errors="replace")
                            parser = _PageTitleParser()
                            parser.feed(source)
                            title = html.unescape(" ".join(parser.parts)).strip()
                            if title and not re.search(r"登入|login", title, re.IGNORECASE):
                                return "影片" if "歡樂電影城" in title else "學習"
        except (OSError, urllib.error.URLError, TimeoutError, ValueError):
            pass
    identifiers = re.findall(r"\d+", urllib.parse.unquote(url))
    return identifiers[0] if identifiers else "未分類"

def _unique_group_name(name: str, groups: list[dict[str, object]]) -> str:
    existing = {str(group["name"]) for group in groups}
    if name not in existing:
        return name
    index = 1
    while f"{name}({index})" in existing:
        index += 1
    return f"{name}({index})"

def _add_course_urls(mgr: "AccountManager", urls: list[str]) -> None:
    groups = load_course_groups()
    added = 0
    known = {_norm_url(u): g["name"] for g in groups for u in g["urls"]}
    fresh, rejected, seen_now = [], [], set()
    for u in urls:
        key = _norm_url(u)
        if key in known:
            rejected.append((u, f"已存在於「{known[key]}」"))
        elif key in seen_now:
            rejected.append((u, "本次輸入中重複"))
        else:
            seen_now.add(key)
            fresh.append(u)
    if rejected:
        note("WARN", f"有 {len(rejected)} 個重複網址，已拒絕加入：")
        for u, why in rejected:
            print(f"      {u}  {DIM}（{why}）{RESET}")
    if not fresh:
        note("WARN", "沒有可加入的新網址，未做任何變更。")
        return
    urls = fresh
    bulk_name = ""
    if len(fresh) > 1:
        try:
            while True:
                bulk_name = input(f"共 {len(fresh)} 個新連結，要全部加入哪個群組？（Enter 逐一自動命名，最多 64 字）：").strip()
                if len(bulk_name) <= 64:
                    break
                note("WARN", "群組名稱不得超過 64 個字，請重新輸入。")
        except (EOFError, KeyboardInterrupt):
            print()
            note("INFO", "已停止新增。")
            return
    for url in urls:
        suggested = bulk_name or _derive_course_group_name(url, mgr)
        while True:
            if bulk_name:
                name = bulk_name
                break
            try:
                name = input(f"群組名稱（Enter 使用「{suggested}」，最多 64 字）：").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                note("INFO", "已停止新增。")
                name = ""
                suggested = ""
                break
            if not name or len(name) <= 64:
                break
            note("WARN", "群組名稱不得超過 64 個字，請重新輸入。")
        if not name and not suggested:
            break
        if not name:
            name = _unique_group_name(suggested, groups)
        group = next(
            (
                item
                for item in groups
                if item["name"] == name
                and str(item.get("category") or item["name"]) == name
            ),
            None,
        )
        if group is None:
            group = {"name": name, "category": name, "urls": []}
            groups.append(group)
        group["urls"].append(url)
        added += 1
    save_course_groups(groups)
    note("DONE", f"已新增 {added} 個連結" + (f"（拒絕 {len(rejected)} 個重複）" if rejected else "") + f"；目前共有 {len(groups)} 組。")

def _remove_course_url() -> None:
    groups = load_course_groups()
    entries = [(group, url) for group in groups for url in group["urls"]]
    if not entries:
        note("INFO", "目前沒有已儲存的連結。")
        return
    if _is_windows_tty():
        cats: dict[str, list[str]] = {}
        for g, u in entries:
            cats.setdefault(str(g.get("category") or g["name"]), []).append(u)
        doomed = _windows_category_picker(cats, f"{CYAN}選擇要刪除的分類{RESET}")
        if not doomed:
            note("INFO", "已取消")
            return
        if _windows_select(["確定刪除", "取消"], f"{CYAN}確定刪除 {len(doomed)} 個連結？{RESET}") != 0:
            note("INFO", "已取消。")
            return
        for g, u in entries:
            if u in doomed and u in g["urls"]:
                g["urls"].remove(u)
        save_course_groups([item for item in groups if item["urls"]])
        note("DONE", f"已刪除 {len(doomed)} 個連結。")
        return
    print("\n已儲存連結：")
    for index, (group, url) in enumerate(entries, 1):
        category = str(group.get("category") or group["name"])
        print(f"  {index}. [{category}] {group['name']}：{url}")
    categories = list(dict.fromkeys(str(group.get("category") or group["name"]) for group in groups))
    print("\n可整類刪除的分類：")
    for category in categories:
        count = sum(
            len(group["urls"])
            for group in groups
            if str(group.get("category") or group["name"]) == category
        )
        print(f"  分類:{category} ({count} 個連結)")
    try:
        choice = input(
            "輸入要刪除的連結編號或分類名稱（分類可輸入 分類:<名稱>；Enter 取消）："
        ).strip()
        if not choice:
            return
        selected_category = choice[len("分類:"):].strip() if choice.startswith("分類:") else None
        if selected_category is None and choice in categories:
            selected_category = choice
        elif selected_category is None:
            try:
                index = int(choice) - 1
            except ValueError:
                selected_category = choice
        if selected_category is not None:
            if selected_category not in categories:
                raise ValueError
            count = sum(
                len(group["urls"])
                for group in groups
                if str(group.get("category") or group["name"]) == selected_category
            )
            confirm = input(
                f"確定刪除分類「{selected_category}」中的 {count} 個連結？ [y/N]: "
            ).strip().lower()
            if confirm not in ("y", "yes"):
                note("INFO", "已取消。")
                return
            remaining = [
                group for group in groups
                if str(group.get("category") or group["name"]) != selected_category
            ]
            save_course_groups(remaining)
            note("DONE", f"已刪除分類「{selected_category}」及其 {count} 個連結。")
            return
        if not 0 <= index < len(entries):
            raise ValueError
        confirm = input("確定刪除此連結？ [y/N]: ").strip().lower()
    except (ValueError, EOFError, KeyboardInterrupt):
        print()
        note("INFO", "已取消或編號無效。")
        return
    if confirm not in ("y", "yes"):
        note("INFO", "已取消。")
        return
    group, url = entries[index]
    group["urls"].remove(url)
    save_course_groups([item for item in groups if item["urls"]])
    note("DONE", f"已刪除連結：{url}")

def cmd_url(mgr: "AccountManager", args: list[str]):
    """Manage saved links; link execution belongs to cool -g."""
    if any(arg in ("-w", "--write", "write") for arg in args):
        cmd_write()
        return
    if args:
        note("WARN", "cool -u 不接受網址參數；請從選單新增或刪除連結。")
        return
    groups = load_course_groups()
    print("\n=== 課程連結管理 ===")
    for group in groups:
        category = str(group.get("category") or group["name"])
        print(f"  [{category}] {group['name']}：{len(group['urls'])} 個連結")
    picked = _arrow_pick(["新增連結", "刪除連結"], f"{CYAN}課程連結管理{RESET}")
    if picked is not None or _is_windows_tty():
        choice = {0: "1", 1: "2"}.get(picked, "")
        if not choice:
            note("INFO", "已取消")
            return
    else:
        print("  1. 新增連結")
        print("  2. 刪除連結")
        try:
            choice = input("請選擇 1/2（Enter 返回）：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
    if choice == "1":
        try:
            raw = _read_paste("請貼上課程連結（可多行貼上，或用空白分隔多個網址）：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        urls = list(dict.fromkeys(
            candidate.rstrip(".,;)>]")
            for candidate in re.findall(r'https?://[^\s"\'<>]+', raw)
        ))
        if not urls:
            note("WARN", "沒有找到有效的 HTTP/HTTPS 網址。")
            return
        _add_course_urls(mgr, urls)
    elif choice == "2":
        _remove_course_url()
    elif choice:
        note("WARN", "選項無效。")

def cmd_go(mgr: "AccountManager", args: list[str]):
    """Select one or more saved link groups and open them in Playwright."""
    mods = _current_mods()
    show_browser = mods.show
    # 允許 a|b、a | b、a,b、a b 等寫法：把所有參數併成同一個選擇字串
    selectors = [" ".join(args).strip()]
    selectors = [x for x in selectors if x]
    groups = load_course_groups()
    if not groups:
        note("WARN", "尚未儲存連結組，請先執行 cool -u 新增。")
        return
    labels = [chr(ord("a") + i) if i < 26 else str(i + 1) for i in range(len(groups))]
    print("\n已儲存的連結組：")
    for label, group in zip(labels, groups):
        category = str(group.get("category") or group["name"])
        print(f"  {label}. [{category}] {group['name']} ({len(group['urls'])} 個連結)")
    try:
        choice = selectors[0] if selectors else input("選擇一組或多組（例如 a|b；Enter 取消）：").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not choice:
        return
    chosen_labels = [item.lower() for item in re.split(r"[|,，、\s]+", choice) if item]
    if not chosen_labels:
        note("WARN", "沒有輸入有效的連結組選項。")
        return
    if "all" in chosen_labels:
        selected = groups
    else:
        selected_indices = []
        for item in chosen_labels:
            if item in labels:
                selected_indices.append(labels.index(item))
            else:
                note("WARN", f"找不到連結組選項「{item}」。")
                return
        selected = [groups[index] for index in dict.fromkeys(selected_indices)]
    urls = list(dict.fromkeys(url for group in selected for url in group["urls"]))
    if not urls:
        note("WARN", "所選連結組沒有可開啟的網址。")
        return
    _run_course_urls(mgr, urls, show_browser, mods.timer)

def _wait_with_timer(page, seconds: int, count: int) -> None:
    """等到計時結束自動回傳；中途按 Enter（或 Ctrl+C）可提前結束。"""
    import threading
    import time as _time

    tty = bool(sys.stdin) and sys.stdin.isatty()
    print(f"\n已開啟 {count} 個連結；{format_duration(seconds)} 後自動關閉瀏覽器（按 Enter 可提前結束）。")
    stop = threading.Event()
    msvcrt = None
    if tty and sys.platform == "win32":
        import msvcrt as _m
        msvcrt = _m
    elif not tty:
        # 桌面應用程式以管線送 Enter：用背景執行緒讀取（行程結束時一併結束）
        def _reader():
            try:
                sys.stdin.readline()
            except Exception:
                pass
            stop.set()
        threading.Thread(target=_reader, daemon=True).start()

    deadline = _time.monotonic() + seconds
    last_shown = -1
    try:
        while not stop.is_set():
            remaining = int(deadline - _time.monotonic() + 0.999)
            if remaining <= 0:
                break
            if remaining != last_shown:
                last_shown = remaining
                if tty:
                    sys.stdout.write(f"\r  剩餘 {format_duration(remaining)}   ")
                    sys.stdout.flush()
                elif remaining % 60 == 0 or remaining <= 10:
                    print(f"  剩餘 {format_duration(remaining)}", flush=True)
            if msvcrt is not None:
                while msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\r", "\n", "\x03"):
                        stop.set()
                if stop.is_set():
                    break
            try:
                page.wait_for_timeout(250)          # 讓 Playwright 事件持續運作
            except Exception:
                _time.sleep(0.25)
    except KeyboardInterrupt:
        stop.set()
    if tty:
        sys.stdout.write("\r" + " " * 30 + "\r")
    if stop.is_set():
        print("已提前結束。")
    else:
        note("INFO", "計時結束，自動關閉瀏覽器。")

def _run_course_urls(mgr: "AccountManager", urls_queue: list[str], show_browser: bool, timer: int | None = None) -> None:
    accounts = mgr.list_accounts()
    if not accounts:
        note("ERR", "尚未登入，請先執行 cool -l。")
        return
    if len(accounts) == 1:
        selected_account = accounts[0]
    else:
        selected_account = _choose_account_interactive(mgr, "請選擇要使用的帳號")
    if not selected_account:
        return
    cookie_path = mgr.get_cookie_path(selected_account["name"])
    if not cookie_path or not cookie_path.is_file():
        note("ERR", f"找不到帳號 {selected_account['name']} 的 Cookie，請重新登入。")
        return
    pw_cookies = []
    try:
        for line in cookie_path.read_text(encoding="utf-8").splitlines():
            is_http_only = line.startswith("#HttpOnly_")
            if is_http_only:
                line = line[len("#HttpOnly_"):]
            elif not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 7:
                continue
            domain, _, path, secure, expiry, name, value = fields[:7]
            try:
                expires = int(expiry)
            except ValueError:
                expires = -1
            pw_cookies.append({
                "name": name, "value": value, "domain": domain.lstrip("."), "path": path or "/",
                "secure": secure.upper() == "TRUE", "httpOnly": is_http_only,
                "expires": expires if expires > 0 else -1, "sameSite": "Lax",
            })
    except OSError as error:
        note("ERR", f"讀取 Cookie 失敗：{error}")
        return
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        note("ERR", "未安裝 Playwright；請依 README 安裝 CLI 依賴後再執行。")
        return

    status_line("啟動 Playwright", "WORK")
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright, headless=not show_browser)
            try:
                context = browser.new_context(**_CONTEXT_OPTS)
                attach_context_logging(context)
                if pw_cookies:
                    context.add_cookies(pw_cookies)
                opened_pages = []
                print(f"\n正在開啟 {len(urls_queue)} 個連結...\n")
                for index, url in enumerate(urls_queue, 1):
                    page = context.new_page()
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=25_000)
                        page.wait_for_timeout(1000)
                        title = page.title().split("|")[0].strip() or url
                        if "login" in page.url.lower() or "logintoken" in page.content()[:2000]:
                            note("WARN", f"[{index}] Cookie 可能失效，已關閉登入頁：{url}")
                            page.close()
                        else:
                            opened_pages.append(page)
                            status_line(f"[{index}] {title[:40]}", "OK")
                    except Exception as error:
                        note("WARN", f"[{index}] 載入失敗：{error}")
                        page.close()
                if not opened_pages:
                    note("ERR", "沒有成功開啟任何課程連結。")
                    return
                if timer:
                    _wait_with_timer(opened_pages[0], timer, len(opened_pages))
                else:
                    print(f"\n已開啟 {len(opened_pages)} 個連結；按 Enter 結束本次工作。")
                    try:
                        input()
                    except (EOFError, KeyboardInterrupt):
                        print()
            finally:
                browser.close()
        status_line("關閉瀏覽器", "DONE")
        note("INFO", "已結束課程工作階段。")
    except Exception as error:
        note("ERR", f"Playwright 執行失敗：{error}")

__all__ = [name for name in globals() if not name.startswith("__")]
