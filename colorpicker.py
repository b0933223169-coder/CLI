"""Interactive color picker and color command."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *

# ============================== colorpicker：cool --color 顏色選單 ==============================

# 項目中文顯示名稱（用於選單標籤）
_ITEM_LABEL_ZH = {
    "title":      "標題外框",
    "title_text": "標題文字",
    "header":     "表頭",
    "cur":        "當月（反色高亮）",
    "low":        "未達標（紅底白字）",
    "url":        "網址列",
    "sep":        "分隔線",
}

def choose_item_curses(colors):
    import curses
    items = list(DEFAULT_COLORS.keys())
    selected = None

    def _menu(stdscr):
        nonlocal selected
        curses.curs_set(0)
        stdscr.keypad(True)
        cur = 0
        # 預先計算最大中文標籤的顯示寬度，用於對齊
        _max_zh_w = max(display_width(_ITEM_LABEL_ZH.get(k, k)) for k in items)
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(0, 0, "選擇要修改的項目 (↑↓ 移動, Enter 確認, Esc 離開)", curses.A_BOLD)
            stdscr.addstr(1, 0, "─" * min(w - 1, 50))
            for i, k in enumerate(items):
                y = 3 + i
                if y >= h - 2:
                    break
                cur_color = colors.get(k, DEFAULT_COLORS[k])
                zh = _ITEM_LABEL_ZH.get(k, k)
                pad = " " * (_max_zh_w - display_width(zh))
                label = f" {zh}{pad}  目前: {cur_color} "
                attr = curses.A_REVERSE | curses.A_BOLD if i == cur else curses.A_NORMAL
                stdscr.addstr(y, 2, label[:w - 4], attr)
            stdscr.addstr(3 + len(items) + 1, 0, "↑↓ 選擇  Enter 確認  Esc 離開")
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

    TILE_W = 6   # 每個色塊佔用的欄寬（含間距）
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
                curses.init_pair(next_pair[0], -1, idx)
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
            stdscr.addstr(0, 0, title[:w - 1], curses.A_BOLD)
            hint = "方向鍵 移動  Enter 確認  / 搜尋  # HEX  r RGB滑桿  v 終端反色  Esc 返回上一步"
            stdscr.addstr(1, 0, hint[:w - 1])
            if query:
                stdscr.addstr(2, 0, f"搜尋: {query}"[:w - 1])

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
                            stdscr.addstr(y, x, "[", curses.A_BOLD)
                            stdscr.addstr(y, x + 1, "    ", attr | curses.A_BOLD)
                            stdscr.addstr(y, x + 5, "]", curses.A_BOLD)
                        else:
                            stdscr.addstr(y, x + 1, "    ", attr)
                        stdscr.addstr(y, x + 7, f"{full_label}（{name}）"[:w - x - 8],
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
                        stdscr.addstr(y, x, "[", curses.A_BOLD)
                        stdscr.addstr(y, x + 1, "    ", attr | curses.A_BOLD)
                        stdscr.addstr(y, x + 5, "]", curses.A_BOLD)
                    else:
                        stdscr.addstr(y, x + 1, "    ", attr)
                    short = DISPLAY_LABEL.get(name, name.replace("COLOR_", "C").replace("BG_", "B"))
                    stdscr.addstr(y + 1, x, short[:TILE_W - 1].ljust(TILE_W - 1),
                                   curses.A_BOLD if is_cur else curses.A_DIM)
                except curses.error:
                    pass

            if names:
                cur_name = names[cur]
                label = DISPLAY_LABEL.get(cur_name)
                shown = f"{cur_name}（{label}）" if label else cur_name
                footer = f"{shown}   ({page_start+1}-{page_end}/{len(names)})"
            else:
                footer = "（無符合結果）"
            stdscr.addstr(h - 1, 0, footer[:w - 1])
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
                stdscr.addstr(2, 0, "搜尋: ")
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
            item = choose_item_curses(colors)
            if not item:
                print("已離開顏色設定")
                return

        chosen = choose_color_curses(colors, item)
        if not chosen:
            # Esc：返回項目選單（若 item 是從命令列直接指定的，也一樣返回選單讓使用者再選）
            item = None
            continue

        colors[item] = chosen
        save_colors(colors)
        zh = _ITEM_LABEL_ZH.get(item, item)
        print(f"已將 {zh}（{item}）設為 {chosen} {_color_preview_block(chosen)}")
        # 儲存後回到項目選單，讓使用者可以繼續修改其他項目
        item = None

def cmd_color(_mgr, args):
    """給 repl/cli 呼叫的橋接函式：忽略帳號物件（顏色設定跟帳號無關），
    直接把參數轉交給 _color_main。"""
    return _color_main(args)

__all__ = [name for name in globals() if not name.startswith("__")]
