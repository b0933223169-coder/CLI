"""Interactive account and login-target selection menus."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *
from .security import *
from .accounts import *

def _windows_select(options, title, footer="↑↓ 移動  Enter 確認  Esc 返回"):
    import msvcrt
    current = 0
    while True:
        os.system("cls")
        print(title)
        print("─" * 52)
        for index, option in enumerate(options):
            marker = ">" if index == current else " "
            print(f"{marker} {option}")
        print()
        print(footer, flush=True)
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H" and current > 0:
                current -= 1
            elif key == "P" and current < len(options) - 1:
                current += 1
        elif key in ("\r", "\n"):
            return current
        elif key == "\x1b":
            return None

def _choose_account_interactive(mgr: AccountManager, title: str = "請選擇帳號"):
    accounts = mgr.list_accounts()
    if not accounts:
        return None
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(f"{CYAN}{title}：{RESET}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {YELLOW}{i}.{RESET} {MAGENTA}{acc['name']}{RESET}  {DIM}({acc['email']}){RESET}")
        try:
            choice = input("輸入編號 (直接 Enter 取消): ").strip()
            if not choice:
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                return accounts[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        note("WARN", "已取消")
        return None
    if os.name == "nt":
        options = [
            f"{acc['name']}  ({acc['email']})"
            for acc in accounts
        ]
        selected = _windows_select(options, f"{CYAN}{title}{RESET}")
        if selected is None:
            note("INFO", "已取消")
            return None
        return accounts[selected]
    try:
        import curses
        selected_idx = None
        action = "select"
        SHIFT_NUMS = {ord('!'): 0, ord('@'): 1, ord('#'): 2, ord('$'): 3, ord('%'): 4, ord('^'): 5, ord('&'): 6, ord('*'): 7, ord('('): 8}

        def _curses_menu(stdscr):
            nonlocal selected_idx, action
            curses.curs_set(0)
            stdscr.keypad(True)
            cur = 0
            confirm_delete = False

            while True:
                stdscr.clear()
                h, w = stdscr.getmaxyx()
                stdscr.addstr(0, 0, f"{title}  (↑/↓ 移動  1-9 跳轉  Shift+1-9 直接選取  Del 刪除  q 取消)"[:w-1])
                stdscr.addstr(1, 0, DIM + "─" * min(w - 1, 65) + RESET)

                for i, acc in enumerate(accounts):
                    y = 3 + i
                    if y >= h - 3:
                        break
                    label = f" [{i+1}] {acc['name']}  ({acc['email']}) "
                    if i == cur:
                        stdscr.addstr(y, 2, label[:w-4], curses.A_REVERSE | curses.A_BOLD)
                    else:
                        stdscr.addstr(y, 2, label[:w-4])

                hint_y = min(h - 2, 3 + len(accounts) + 1)
                if confirm_delete:
                    warn_msg = f" ⚠️ 確定要刪除帳號 [{accounts[cur]['name']}] 嗎？ 按 [y] 確認刪除，其他鍵取消 "
                    stdscr.addstr(hint_y, 0, warn_msg[:w-1], curses.A_REVERSE | curses.A_BOLD)
                else:
                    stdscr.addstr(hint_y, 0, DIM + "操作：上下鍵移動 | 1-9 跳轉 | Shift+1-9 獨佔直選 | Del/d 刪除 | Enter 確認"[:w-1] + RESET)

                stdscr.refresh()
                key = stdscr.getch()

                if confirm_delete:
                    if key in (ord('y'), ord('Y')):
                        action = "delete"
                        selected_idx = cur
                        break
                    else:
                        confirm_delete = False
                    continue

                if key == curses.KEY_UP and cur > 0:
                    cur -= 1
                elif key == curses.KEY_DOWN and cur < len(accounts) - 1:
                    cur += 1
                elif ord('1') <= key <= ord('9'):
                    target = key - ord('1')
                    if target < len(accounts):
                        cur = target
                elif key in SHIFT_NUMS:
                    target = SHIFT_NUMS[key]
                    if target < len(accounts):
                        selected_idx = target
                        action = "select"
                        break
                elif key in (curses.KEY_DC, ord('d'), ord('D')):
                    confirm_delete = True
                elif key in (10, 13, curses.KEY_ENTER):
                    selected_idx = cur
                    action = "select"
                    break
                elif key in (27, ord('q'), ord('Q')):
                    selected_idx = None
                    break

        curses.wrapper(_curses_menu)
        if selected_idx is None:
            note("INFO", "已取消")
            return None

        if action == "delete":
            del_target = accounts[selected_idx]
            ok, info = mgr.remove(del_target["name"])
            if ok:
                status_line("刪除帳號", "DONE")
                note("INFO", f"已安全刪除帳號：{del_target['name']} ({del_target['email']})")
            else:
                status_line("刪除帳號", "FAILED")
                note("ERR", str(info))
            return None

        return accounts[selected_idx]
    except Exception as e:
        note("WARN", f"curses 選單失敗 ({e})，改用數字選單")
        print(f"{CYAN}{title}：{RESET}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {YELLOW}{i}.{RESET} {MAGENTA}{acc['name']}{RESET}  {DIM}({acc['email']}){RESET}")
        try:
            choice = input("輸入編號 (直接 Enter 取消): ").strip()
            if not choice:
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                return accounts[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        note("WARN", "已取消")
        return None

def _choose_login_target(mgr: AccountManager):
    accounts = mgr.list_accounts()
    new_label = "➕ 輸入新帳號"
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(f"{CYAN}選擇登入對象（Esc 直接取消）：{RESET}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {YELLOW}{i}.{RESET} {MAGENTA}{acc['name']}{RESET}  {DIM}({acc['email']}){RESET}")
        print(f"  {YELLOW}{len(accounts)+1}.{RESET} {GREEN}{new_label}{RESET}")
        print(f"  {DIM}提示：輸入編號後 Enter，Esc/直接 Enter 返回上一部{RESET}")
        try:
            choice = input("輸入編號: ").strip()
            if not choice:
                return "cancel"
            if choice.lower() == "esc":
                return "cancel"
            idx = int(choice) - 1
            if idx == len(accounts):
                return None
            if 0 <= idx < len(accounts):
                return accounts[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        return "cancel"
    if os.name == "nt":
        options = [
            f"{acc['name']}  ({acc['email']})"
            for acc in accounts
        ]
        options.append(new_label)
        selected = _windows_select(
            options,
            f"{CYAN}選擇登入對象{RESET}",
        )
        if selected is None:
            return "cancel"
        if selected == len(accounts):
            return None
        return accounts[selected]
    try:
        import curses
        selected = None
        def _menu(stdscr):
            nonlocal selected
            curses.curs_set(0)
            stdscr.keypad(True)
            cur = 0
            total = len(accounts) + 1
            while True:
                stdscr.clear()
                stdscr.addstr(0, 0, "選擇登入對象  (↑/↓ 移動  Enter 確認  Esc 返回)")
                stdscr.addstr(1, 0, DIM + "─" * 52 + RESET)
                for i, acc in enumerate(accounts):
                    y = 3 + i
                    label = f" {acc['name']}  ({acc['email']}) "
                    attr = curses.A_REVERSE | curses.A_BOLD if i == cur else curses.A_NORMAL
                    stdscr.addstr(y, 2, label, attr)
                y_new = 3 + len(accounts)
                label_new = f" {new_label} "
                attr_new = curses.A_REVERSE | curses.A_BOLD if cur == len(accounts) else curses.A_NORMAL
                stdscr.addstr(y_new, 2, label_new, attr_new)
                stdscr.addstr(y_new + 2, 0, DIM + "Esc 返回上一部" + RESET)
                stdscr.refresh()
                key = stdscr.getch()
                if key == curses.KEY_UP and cur > 0:
                    cur -= 1
                elif key == curses.KEY_DOWN and cur < total - 1:
                    cur += 1
                elif key in (10, 13, curses.KEY_ENTER):
                    if cur == len(accounts):
                        selected = None
                    else:
                        selected = accounts[cur]
                    break
                elif key == 27:
                    selected = "cancel"
                    break
                elif key in (ord('q'), ord('Q')):
                    selected = "cancel"
                    break
                elif key == curses.KEY_RESIZE:
                    pass
        curses.wrapper(_menu)
        return selected
    except Exception as e:
        note("WARN", f"curses 選單失敗 ({e})，改用數字選單")
        print(f"{CYAN}選擇登入對象：{RESET}")
        for i, acc in enumerate(accounts, 1):
            print(f"  {YELLOW}{i}.{RESET} {MAGENTA}{acc['name']}{RESET}  {DIM}({acc['email']}){RESET}")
        print(f"  {YELLOW}{len(accounts)+1}.{RESET} {GREEN}{new_label}{RESET}")
        try:
            choice = input("輸入編號 (Esc/Enter 返回): ").strip()
            if not choice or choice.lower() == "esc":
                return "cancel"
            idx = int(choice) - 1
            if idx == len(accounts):
                return None
            if 0 <= idx < len(accounts):
                return accounts[idx]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        return "cancel"

__all__ = [name for name in globals() if not name.startswith("__")]
