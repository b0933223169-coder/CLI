"""Saved-course URL management and browser command."""
from __future__ import annotations
from .._compat import *
from ..paths import *
from ..colors import *
from ..security import *
from ..accounts import *
from ..ui import *

def load_urls() -> list[str]:
    """讀取儲存的課程網址清單。"""
    if not URLS_FILE.exists():
        return []
    try:
        lines = URLS_FILE.read_text(encoding="utf-8").splitlines()
        urls = []
        for l in lines:
            l = l.strip()
            if l and not l.startswith("#") and (l.startswith("http://") or l.startswith("https://")):
                if l not in urls:
                    urls.append(l)
        return urls
    except Exception:
        return []

def save_urls(urls: list[str]):
    """將網址清單排版並寫入 urls.txt。"""
    header = [
        "# Cool English 課程網址清單",
        f"# 最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# 每行一個網址，支援 cool -u 快速選取或依序瀏覽",
        "",
    ]
    data = "\n".join(header + urls) + "\n"
    _atomic_write(URLS_FILE, data, 0o600)

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

    # 規範化與去重
    cleaned_urls = []
    for u in found_urls:
        u = u.rstrip(".,;)>]")
        if u not in cleaned_urls:
            cleaned_urls.append(u)

    existing = load_urls()
    total = list(existing)
    added_count = 0
    for u in cleaned_urls:
        if u not in total:
            total.append(u)
            added_count += 1

    save_urls(total)
    status_line("網址排版與儲存", "DONE")
    note("INFO", f"本次解析出 {len(cleaned_urls)} 個網址，新增 {added_count} 個，清單總計 {len(total)} 個。")
    print(f"\n{CYAN}目前已儲存的課程網址清單：{RESET}")
    for idx, u in enumerate(total, 1):
        print(f"  {YELLOW}{idx:2d}.{RESET} {u}")
    print()
    return total

def _choose_url_interactive(urls: list[str]) -> list[str] | str | None:
    """提供互動式清單選擇要訪問的網址。"""
    if not urls:
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
                # 數字鍵 (1~9) 或空白鍵：勾選網址。
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
                # Delete 鍵 (所有刪除操作均進入防呆確認)
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

def cmd_url(mgr: AccountManager, args: list[str]):
    """用 cookie 訪問指定 URL，保持瀏覽器開著讓伺服器記錄停留時間。"""
    if not mgr.list_accounts():
        status_line("檢查登入狀態", "FAILED")
        note("ERR", "尚未登入，請先執行： cool -l")
        return

    show_browser = any(a in ("-s", "--show") for a in args)
    args = [a for a in args if a not in ("-s", "--show")]

    # 檢查是否有 -w / --write 參數
    want_write = any(a in ("-w", "--write", "write") for a in args)
    args = [a for a in args if a not in ("-w", "--write", "write")]

    if want_write:
        cmd_write()
        return

    # 解析參數：cool -u [帳號] [URL]
    target_url = None
    account_id = None
    remaining = list(args)

    # 先從 args 裡找 URL（http 開頭）
    for a in list(remaining):
        if a.startswith("http://") or a.startswith("https://"):
            target_url = a
            remaining.remove(a)
            break

    # 剩下的當帳號名
    if remaining:
        maybe = " ".join(remaining).strip()
        acc_found = mgr.find(maybe)
        if acc_found:
            account_id = acc_found["name"]
        else:
            note("WARN", f"找不到帳號: {maybe}，將使用預設帳號")

    # 選帳號
    if account_id is None:
        if len(mgr.list_accounts()) == 1:
            account_id = mgr.list_accounts()[0]["name"]
            note("INFO", f"自動使用帳號：{account_id}")
        else:
            chosen = _choose_account_interactive(mgr, "請選擇要使用的帳號")
            if not chosen:
                return
            account_id = chosen["name"]

    # 取 cookie
    cookie_path = mgr.get_cookie_path(account_id)
    if cookie_path is None or not cookie_path.exists():
        status_line("檢查 cookie", "FAILED")
        note("ERR", f"找不到帳號 {account_id} 的 cookie，請重新 -l 登入")
        return

    acc = mgr.get_account_for_cookie(cookie_path)
    acc_label = f"{acc['name']} ({acc['email']})" if acc else str(cookie_path)
    note("INFO", f"使用帳號：{acc_label}")

    # 若未帶 URL，檢查已儲存清單或提示輸入
    urls_queue = []
    if not target_url:
        saved_urls = load_urls()
        if saved_urls:
            selected = _choose_url_interactive(saved_urls)
            if not selected:
                return
            if selected == "ALL":
                urls_queue = list(saved_urls)
            elif isinstance(selected, list):
                urls_queue = selected
            else:
                urls_queue = [selected]
        else:
            try:
                target_url = input("請貼入課程 URL（或輸入 -w 批量寫入）：").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                note("INFO", "已取消")
                return
            if target_url in ("-w", "--write", "write"):
                cmd_write()
                return
            if not target_url.startswith("http"):
                note("ERR", f"無效 URL：{target_url}")
                return
            urls_queue = [target_url]
    else:
        urls_queue = [target_url]

    # 讀 cookie 轉 Playwright 格式
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
    except Exception as e:
        note("ERR", f"讀取 cookie 失敗：{e}")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        note("ERR", "未安裝 playwright，請執行：pip install playwright && playwright install chromium")
        return

    status_line("啟動 Playwright", "WORK")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not show_browser)
            ctx = browser.new_context(user_agent=UA)
            if pw_cookies:
                try:
                    ctx.add_cookies(pw_cookies)
                except Exception as ce:
                    note("WARN", f"注入 cookie 失敗：{ce}")

            opened_pages = []
            print(f"\n{CYAN}正在同時開啟 {len(urls_queue)} 個分頁...{RESET}\n")

            for i, current_url in enumerate(urls_queue, 1):
                page = ctx.new_page()
                try:
                    page.goto(current_url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(1000)
                    title = ""
                    try:
                        title = page.title().split("|")[0].strip()
                    except Exception:
                        title = current_url

                    final_url = page.url
                    if "login" in final_url.lower() or "logintoken" in page.content()[:2000]:
                        note("WARN", f"[分頁 {i}] session 已過期（導向登入頁）：{current_url}")
                        page.close()
                    else:
                        opened_pages.append((i, page, title, current_url))
                        status_line(f"分頁 [{i}] {title[:20]}", "OK")
                except Exception as ge:
                    note("WARN", f"[分頁 {i}] 載入超時或失敗：{ge}")

            if not opened_pages:
                note("ERR", "所有分頁載入失敗或 session 已失效")
                browser.close()
                return

            print(f"\n{GREEN}✅ 已成功同時開啟 {len(opened_pages)} 個分頁！{RESET}")
            print(f"{YELLOW}所有分頁正在背景同時累積學習時數中...{RESET}")
            print(f"{DIM}按 Enter 鍵可同時關閉所有分頁並結束掛機{RESET}\n")

            try:
                input()
            except (EOFError, KeyboardInterrupt):
                print()

            browser.close()
            status_line("關閉所有分頁與瀏覽器", "DONE")
            note("INFO", "已結束訪問，可用 cool -t 確認時數是否增加")
    except Exception as e:
        note("ERR", f"Playwright 執行失敗：{e}")

__all__ = [name for name in globals() if not name.startswith("__")]
