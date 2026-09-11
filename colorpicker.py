"""Interactive color picker and color command."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *

# ============================== colorpicker：cool --color 顏色選單 ==============================

# 項目中文顯示名稱（用於選單標籤）
_ITEM_LABEL_ZH = {
    "title":      "標題",
    "title_text": "標題文字",
    "header":     "表頭",
    "cur":        "當月",
    "low":        "未達標",
    "url":        "網址列",
    "sep":        "分隔線",
}

def _xterm256_rgb(index):
    """Convert an xterm-256 index to RGB for Windows ANSI rendering."""
    index = max(0, min(255, int(index)))
    if index < 16:
        basic = (
            (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
            (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
            (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
            (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
        )
        return basic[index]
    if index < 232:
        value = (0, 95, 135, 175, 215, 255)
        n = index - 16
        return value[n // 36], value[(n // 6) % 6], value[n % 6]
    gray = 8 + (index - 232) * 10
    return gray, gray, gray

def _windows_swatch(name):
    """Render one solid ANSI swatch with the exact xterm color."""
    if name.startswith(("COLOR_", "BG_")):
        index = int(name.rsplit("_", 1)[1])
        r, g, b = _xterm256_rgb(index)
        return f"\033[48;2;{r};{g};{b}m    \033[0m"
    if name == "REVERSE":
        return "\033[7m    \033[0m"
    return f"{_swatch_ansi(name)}    {RESET}"

def _fit_curses_text(text, width):
    """截斷文字但保留完整的色名與中文字寬度，避免 curses 直接丟掉尾端內容。"""
    if width <= 0:
        return ""
    result = []
    used = 0
    for char in str(text):
        char_width = display_width(char)
        if used + char_width > width:
            break
        result.append(char)
        used += char_width
    return "".join(result)

def _safe_addstr(stdscr, y, x, text, attr=0):
    import curses
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    text = _fit_curses_text(text, max(0, w - x - 1))
    if not text:
        return
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        # Windows curses rejects writes touching the lower-right cell.
        try:
            stdscr.addnstr(y, x, text, max(0, w - x - 1), attr)
        except curses.error:
            pass

def choose_item_windows(colors):
    """Windows-native item menu; avoids curses Unicode rendering truncation."""
    import msvcrt

    items = list(DEFAULT_COLORS.keys())
    cur = 0
    while True:
        os.system("cls")
        print("選擇要修改的項目 (↑↓ 移動, Enter 確認, Esc 離開)")
        print("─" * 50)
        for i, key in enumerate(items):
            marker = ">" if i == cur else " "
            label = _ITEM_LABEL_ZH.get(key, key)
            value = colors.get(key, DEFAULT_COLORS[key])
            print(f"{marker} {label}  目前: {value}")
        print()
        print("↑↓ 選擇  Enter 確認  Esc 離開", flush=True)

        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H" and cur > 0:
                cur -= 1
            elif key == "P" and cur < len(items) - 1:
                cur += 1
        elif key in ("\r", "\n"):
            return items[cur]
        elif key == "\x1b":
            return None

def choose_item_curses(colors):
    import curses
    items = list(DEFAULT_COLORS.keys())
    selected = None

    def _menu(stdscr):
        nonlocal selected
        curses.curs_set(0)
        stdscr.keypad(True)
        cur = 0
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            header = "選擇要修改的項目 (↑↓ 移動, Enter 確認, Esc 離開)"
            header_wrapped = w < 70
            if header_wrapped:
                _safe_addstr(stdscr, 0, 0, "選擇要修改的項目", curses.A_BOLD)
                _safe_addstr(stdscr, 1, 0, "(↑↓ 移動, Enter 確認, Esc 離開)", curses.A_BOLD)
            else:
                _safe_addstr(stdscr, 0, 0, header, curses.A_BOLD)
            _safe_addstr(stdscr, 2 if header_wrapped else 1, 0,
                         "─" * min(w - 1, 50))
            start_y = 3 if header_wrapped else 2
            for i, k in enumerate(items):
                y = start_y + i
                if y >= h - 3:
                    break
                cur_color = colors.get(k, DEFAULT_COLORS[k])
                zh = _ITEM_LABEL_ZH.get(k, k)
                attr = curses.A_NORMAL
                stdscr.move(y, 0)
                stdscr.clrtoeol()
                _safe_addstr(
                    stdscr, y, 0, ">" if i == cur else " ",
                    curses.A_BOLD if i == cur else curses.A_NORMAL,
                )
                _safe_addstr(stdscr, y, 2, f"{zh}  目前: {cur_color}", attr)
            footer_y = start_y + len(items) + 1
            _safe_addstr(stdscr, min(h - 1, footer_y), 0,
                         "↑↓ 選擇  Enter 確認  Esc 離開")
            stdscr.refresh()
            ch = stdscr.getch()
            if ch == curses.KEY_UP and cur > 0:
                cur -= 1
            elif ch == curses.KEY_DOWN and cur < len(items) - 1:
                cur += 1
            elif ch in (10, 13, curses.KEY_ENTER):
                selected = items[cur]
                break
            elif ch in (27, ord('q')):
                break

    curses.wrapper(_menu)
    return selected

def choose_color_windows(colors, item):
    """Windows-native color grid; keeps swatches without a curses dependency."""
    import msvcrt
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            for handle in (kernel32.GetStdHandle(-11), kernel32.GetStdHandle(-12)):
                mode = ctypes.c_uint()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except (AttributeError, OSError):
            pass

    categories = [
        ("256 色（前景）", [f"COLOR_{i:03d}" for i in range(256)] + ["REVERSE"]),
        ("256 色（背景）", [f"BG_{i:03d}" for i in range(256)] + ["REVERSE"]),
    ]
    cell_width = 12
    category = 0
    current = colors.get(item, DEFAULT_COLORS.get(item, ""))
    cur = 0
    if current.startswith("COLOR_"):
        category = 0
        cur = int(current.split("_", 1)[1])
    elif current.startswith("BG_"):
        category = 1
        cur = int(current.split("_", 1)[1])
    elif current == "REVERSE":
        cur = 0

    def layout():
        terminal = shutil.get_terminal_size((80, 24))
        width = terminal.columns
        height = terminal.lines
        cols = max(1, (width - 2) // cell_width)
        # Header (3), separator (1), each grid row (2), footer (2).
        rows = max(1, (height - 8) // 2)
        return cols, rows, cols * rows

    def draw():
        cols, rows, page_size = layout()
        names = categories[category][1]
        page = cur // page_size
        start = page * page_size
        end = min(start + page_size, len(names))
        os.system("cls")
        print(
            f"為 [{_ITEM_LABEL_ZH.get(item, item)}] 選擇顏色  "
            f"{categories[category][0]}  (Tab 切換分類)"
        )
        print("方向鍵 移動  Enter 確認  Tab 分類  PgUp/PgDn 翻頁  Esc 返回")
        print(f"目前: {current}")
        print("─" * (cols * cell_width))
        for row in range(rows):
            swatches = []
            labels = []
            for col in range(cols):
                index = start + row * cols + col
                if index >= end:
                    swatches.append("")
                    labels.append("")
                    continue
                name = names[index]
                marker = "[" if index == cur else " "
                close = "]" if index == cur else " "
                swatch = _windows_swatch(name)
                cell = f"{marker}{swatch}{close}"
                visible = 6
                left = max(0, (cell_width - visible) // 2)
                swatches.append(" " * left + cell + " " * (cell_width - left - visible))
                labels.append(name.ljust(cell_width))
            print("".join(swatches))
            print("".join(labels))
        print("─" * (cols * cell_width))
        print(f"{start + 1}-{end}/{len(names)}", flush=True)

    while True:
        draw()
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            names = categories[category][1]
            cols, rows, page_size = layout()
            if key == "H":
                cur = max(0, cur - cols)
            elif key == "P":
                cur = min(len(names) - 1, cur + cols)
            elif key == "K" and cur > 0:
                cur -= 1
            elif key == "M" and cur < len(names) - 1:
                cur += 1
            elif key == "I":
                cur = max(0, cur - page_size)
            elif key == "Q":
                cur = min(len(names) - 1, cur + page_size)
        elif key in ("\r", "\n"):
            current = categories[category][1][cur]
            return current
        elif key == "\t":
            category = (category + 1) % len(categories)
            current = categories[category][1][cur]
        elif key == "\x1b":
            return None

# ---------- curses 選單：顏色選擇（方向鍵導覽 + 即時色塊預覽 + 分類 + 搜尋 + RGB 滑桿） ----------
def choose_color_curses(colors, item):
    import curses

    fg256 = [f"COLOR_{i:03d}" for i in range(256)] + ["REVERSE"]
    bg256 = [f"BG_{i:03d}" for i in range(256)] + ["REVERSE"]

    categories = [
        ("256 色（前景）", fg256),
        ("256 色（背景）", bg256),
    ]

    selected = None
    want_hex_prompt = False
    want_rgb_prompt = False

    TILE_W = 10  # 保留 COLOR_232 / BG_232 完整名稱（含間距）
    TILE_H = 2   # 每個色塊佔用的列高（色塊本體 + 名稱）

    def _menu(stdscr):
        nonlocal selected, want_hex_prompt, want_rgb_prompt
        curses.curs_set(0)
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        stdscr.keypad(True)

        has_256 = curses.COLORS >= 256
        pair_cache = {}   # xterm 索引 -> curses color_pair 編號
        next_pair = [1]   # pair 0 保留給 curses 用，所以從 1 開始

        def pair_for(idx):
            idx = idx if has_256 else min(7, idx // 32)
            if idx in pair_cache:
                return pair_cache[idx]
            if next_pair[0] >= curses.COLOR_PAIRS:
                return 0
            try:
                # Windows curses 對預設前景色 -1 支援不完整，明確指定白色
                # 才能讓色塊與文字在按鍵放開後仍保持可見。
                curses.init_pair(next_pair[0], curses.COLOR_WHITE, idx)
            except curses.error:
                return 0
            pair_cache[idx] = next_pair[0]
            next_pair[0] += 1
            return pair_cache[idx]

        def tile_attr(name):
            kind, val = _swatch_kind(name)
            if kind == "reverse":
                return curses.A_REVERSE
            if kind == "index":
                pid = pair_for(val)
                return curses.color_pair(pid) if pid else curses.A_DIM
            return curses.A_DIM

        cat = 0
        cur = 0
        query = ""
        REVERSE_SENTINEL = "REVERSE"

        # 根據目前已設定的顏色，自動定位游標到對應色塊
        _current = colors.get(item, DEFAULT_COLORS.get(item, ""))
        if _current.startswith("COLOR_"):
            try:
                cur = int(_current.split("_")[1])   # COLOR_129 → idx 129
                cat = 0
            except (ValueError, IndexError):
                pass
        elif _current.startswith("BG_"):
            try:
                cur = int(_current.split("_")[1])   # BG_037 → idx 37
                cat = 1
            except (ValueError, IndexError):
                pass
        elif _current == "REVERSE":
            cat = 0
            cur = len(fg256) - 1                    # REVERSE 永遠在 fg256 最後一項

        def visible_list(cols):
            raw = categories[cat][1]
            if query:
                filtered = [n for n in raw if query.lower() in n.lower()]
            else:
                filtered = list(raw)
            if REVERSE_SENTINEL in filtered:
                # 讓「終端反色」永遠自己獨立一整行，排在整個色盤網格最後面
                core = [n for n in filtered if n != REVERSE_SENTINEL]
                pad = (-len(core)) % cols if cols else 0
                return core + [None] * pad + [REVERSE_SENTINEL]
            return filtered

        def clamp_valid(names, idx, direction):
            if not names:
                return 0
            idx = max(0, min(len(names) - 1, idx))
            while names[idx] is None:
                nxt = idx + direction
                if nxt < 0 or nxt >= len(names):
                    break
                idx = nxt
            return idx

        while True:
            h, w = stdscr.getmaxyx()
            cols = max(1, w // TILE_W)
            names = visible_list(cols)
            if not names:
                cur = 0
            else:
                cur = clamp_valid(names, cur, 1)

            stdscr.clear()
            title = f"為 [{_ITEM_LABEL_ZH.get(item, item)}（{item}）] 選擇顏色  分類: {categories[cat][0]} (Tab 切換分類)"
            _safe_addstr(stdscr, 0, 0, title, curses.A_BOLD)
            hint = "方向鍵 移動  Enter 確認  / 搜尋  # HEX  r RGB滑桿  v 終端反色  Esc 返回上一步"
            _safe_addstr(stdscr, 1, 0, hint)
            if query:
                _safe_addstr(stdscr, 2, 0, f"搜尋: {query}")

            grid_top = 4
            rows_per_page = max(1, (h - grid_top - 2) // TILE_H)
            per_page = cols * rows_per_page

            cur_row_all = cur // cols
            page = cur_row_all // rows_per_page
            page_start = page * per_page
            page_end = min(page_start + per_page, len(names))

            for i in range(page_start, page_end):
                name = names[i]
                if name is None:
                    continue
                idx_in_page = i - page_start
                r = idx_in_page // cols
                c = idx_in_page % cols
                y = grid_top + r * TILE_H
                is_cur = (i == cur)
                if name == "REVERSE":
                    # 獨立一整行、用完整名稱標示，跟其他色塊分開
                    x = 0
                    if y + 1 >= h:
                        continue
                    attr = tile_attr(name)
                    full_label = DISPLAY_LABEL.get(name, name)
                    try:
                        if is_cur:
                            _safe_addstr(stdscr, y, x, "[", curses.A_BOLD)
                            _safe_addstr(stdscr, y, x + 1, "    ", attr | curses.A_BOLD)
                            _safe_addstr(stdscr, y, x + 5, "]", curses.A_BOLD)
                        else:
                            _safe_addstr(stdscr, y, x + 1, "    ", attr)
                        _safe_addstr(stdscr, y, x + 7, f"{full_label}（{name}）",
                                     curses.A_BOLD if is_cur else curses.A_NORMAL)
                    except curses.error:
                        pass
                    continue
                x = c * TILE_W
                if y + 1 >= h:
                    continue
                attr = tile_attr(name)
                try:
                    if is_cur:
                        _safe_addstr(stdscr, y, x, "[", curses.A_BOLD)
                        _safe_addstr(stdscr, y, x + 1, "    ", attr | curses.A_BOLD)
                        _safe_addstr(stdscr, y, x + 5, "]", curses.A_BOLD)
                    else:
                        _safe_addstr(stdscr, y, x + 1, "    ", attr)
                    short = DISPLAY_LABEL.get(name, name)
                    _safe_addstr(stdscr, y + 1, x, short.ljust(TILE_W - 1),
                                 attr | (curses.A_BOLD if is_cur else curses.A_NORMAL))
                except curses.error:
                    pass

            if names:
                cur_name = names[cur]
                label = DISPLAY_LABEL.get(cur_name)
                shown = f"{cur_name}（{label}）" if label else cur_name
                footer = f"{shown}   ({page_start+1}-{page_end}/{len(names)})"
            else:
                footer = "（無符合結果）"
            _safe_addstr(stdscr, h - 1, 0, footer)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch == curses.KEY_RIGHT:
                if cur < len(names) - 1:
                    cur = clamp_valid(names, cur + 1, 1)
            elif ch == curses.KEY_LEFT:
                if cur > 0:
                    cur = clamp_valid(names, cur - 1, -1)
            elif ch == curses.KEY_DOWN:
                if cur + cols < len(names):
                    cur = clamp_valid(names, cur + cols, 1)
                elif len(names):
                    cur = clamp_valid(names, len(names) - 1, -1)
            elif ch == curses.KEY_UP:
                if cur - cols >= 0:
                    cur = clamp_valid(names, cur - cols, -1)
                else:
                    cur = clamp_valid(names, 0, 1)
            elif ch == 9:  # Tab
                cat = (cat + 1) % len(categories)
                cur = 0
                query = ""
            elif ch in (10, 13, curses.KEY_ENTER):
                if names and names[cur] is not None:
                    selected = names[cur]
                break
            elif ch in (27,):
                break

            if ch == ord('/'):
                curses.echo()
                _safe_addstr(stdscr, 2, 0, "搜尋: ")
                stdscr.clrtoeol()
                stdscr.refresh()
                try:
                    query = stdscr.getstr(2, 7, 30).decode("utf-8")
                except Exception:
                    query = ""
                curses.noecho()
                cur = 0
            elif ch == ord('#'):
                want_hex_prompt = True
                break
            elif ch == ord('r'):
                want_rgb_prompt = True
                break
            elif ch == ord('v'):
                selected = "REVERSE"
                break

    curses.wrapper(_menu)

    # 這兩個都需要離開 curses 畫面後才能安全執行（curses.wrapper 已經在
    # 回傳前正確呼叫過 endwin()，這裡不能再手動呼叫第二次，否則會噴
    # 「endwin() returned ERR」）
    if want_hex_prompt:
        hex_in = input("輸入 HEX 真彩 (例 #ff00aa): ").strip()
        if hex_in.startswith("#") and _hex_to_ansi(hex_in):
            selected = hex_in
    elif want_rgb_prompt:
        selected = rgb_slider_prompt()

    return selected

def _rgb_to_xterm256(r, g, b):
    """把 24-bit RGB 概略對應到最接近的 xterm 256 色索引，
    用來在 curses 內畫色塊預覽（curses 不支援直接套用任意 truecolor 色塊）。"""
    def chan(v):
        return 0 if v < 48 else min(5, (v - 35) // 40)
    ri, gi, bi = chan(r), chan(g), chan(b)
    return 16 + 36 * ri + 6 * gi + bi

def rgb_slider_prompt():
    """終端外的簡易 RGB 滑桿：用左右鍵調整 R/G/B，Tab 切換通道，Enter 確認。"""
    import curses

    rgb = [128, 128, 128]
    chan = 0
    result = None

    def _slider(stdscr):
        nonlocal result, chan
        curses.curs_set(0)
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        stdscr.keypad(True)
        has_256 = curses.COLORS >= 256
        try:
            curses.init_pair(1, -1, 0)
        except curses.error:
            pass
        cached_idx = None
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(0, 0, "RGB 滑桿  ←→ 調整  Tab 切換 R/G/B  Enter 確認  Esc 取消", curses.A_BOLD)
            labels = ["R", "G", "B"]
            for i in range(3):
                attr = curses.A_REVERSE | curses.A_BOLD if i == chan else curses.A_NORMAL
                bar = "█" * (rgb[i] // 8)
                stdscr.addstr(2 + i, 0, f"{labels[i]}: {rgb[i]:3d} {bar}"[:w - 1], attr)
            hexcode = "#{:02x}{:02x}{:02x}".format(*rgb)
            stdscr.addstr(6, 0, f"HEX: {hexcode}")
            idx = _rgb_to_xterm256(*rgb) if has_256 else min(7, sum(rgb) // 3 // 32)
            if idx != cached_idx:
                try:
                    curses.init_pair(1, -1, idx)
                except curses.error:
                    pass
                cached_idx = idx
            try:
                stdscr.addstr(8, 0, "    ", curses.color_pair(1))
                stdscr.addstr(8, 5, "(近似預覽，實際套用時是精確 truecolor)"[:w - 6], curses.A_DIM)
            except curses.error:
                pass
            stdscr.refresh()
            ch = stdscr.getch()
            if ch == curses.KEY_LEFT:
                rgb[chan] = max(0, rgb[chan] - 5)
            elif ch == curses.KEY_RIGHT:
                rgb[chan] = min(255, rgb[chan] + 5)
            elif ch == 9:
                chan = (chan + 1) % 3
            elif ch in (10, 13, curses.KEY_ENTER):
                result = hexcode
                break
            elif ch == 27:
                break

    curses.wrapper(_slider)
    return result


def _color_main(args):
    colors = load_colors()
    changes = []

    if args and args[0] == "set":
        if len(args) < 3:
            print("用法: python3 cool.py -c set <項目> <顏色>")
            sys.exit(1)
        item, color = args[1], args[2]
        if item not in DEFAULT_COLORS:
            print(f"未知項目: {item}")
            sys.exit(1)
        if color.startswith("#"):
            if not _hex_to_ansi(color):
                print(f"無效 HEX: {color}")
                sys.exit(1)
        elif color not in AVAILABLE_COLORS:
            print(f"未知顏色: {color}")
            sys.exit(1)
        colors[item] = color
        save_colors(colors)
        print(f"已將 {item} 設為 {color} {_color_preview_block(color)}")
        return

    item = None
    if args:
        maybe_item = args[0]
        if maybe_item in DEFAULT_COLORS:
            item = maybe_item
        else:
            print(f"未知項目: {maybe_item}，可用項目: {', '.join(DEFAULT_COLORS.keys())}")
            sys.exit(1)

    # 用迴圈實現「Esc 從顏色選單返回項目選單」
    while True:
        if item is None:
            item = choose_item_windows(colors) if os.name == "nt" else choose_item_curses(colors)
            if not item:
                print("已離開顏色設定")
                if changes:
                    print("\n本次變更：")
                    for change in changes:
                        zh, key, previous, chosen = change
                        old_preview = (
                            _windows_swatch(previous)
                            if os.name == "nt"
                            else _color_preview_block(previous)
                        )
                        new_preview = (
                            _windows_swatch(chosen)
                            if os.name == "nt"
                            else _color_preview_block(chosen)
                        )
                        print(f"  {zh}（{key}）")
                        print(f"    原本: {previous} {old_preview}")
                        print(f"    現在: {chosen} {new_preview}")
                else:
                    print("本次沒有變更顏色。")
                return

        chosen = (
            choose_color_windows(colors, item)
            if os.name == "nt"
            else choose_color_curses(colors, item)
        )
        if not chosen:
            # Esc：返回項目選單（若 item 是從命令列直接指定的，也一樣返回選單讓使用者再選）
            item = None
            continue

        previous = colors.get(item, DEFAULT_COLORS.get(item, "RESET"))
        colors[item] = chosen
        save_colors(colors)
        zh = _ITEM_LABEL_ZH.get(item, item)
        if previous != chosen:
            changes.append((zh, item, previous, chosen))
        # 儲存後回到項目選單，讓使用者可以繼續修改其他項目
        item = None

def cmd_color(_mgr, args):
    """給 repl/cli 呼叫的橋接函式：忽略帳號物件（顏色設定跟帳號無關），
    直接把參數轉交給 _color_main。"""
    return _color_main(args)

__all__ = [name for name in globals() if not name.startswith("__")]
