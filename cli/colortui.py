"""cool -c 的全新顏色設定介面（Windows 終端機）。

設計重點
- 用「備用畫面 + 游標歸位」重繪，整個畫面一次寫出，不再 `cls` 造成閃爍。
- 上方永遠有「報表即時預覽」：移動色票時預覽立刻改變，Enter 才儲存、Esc 還原。
- 色票分頁：常用 36 色、256 色前景／背景、真彩色色相盤（終端三色用）、HEX 輸入。
- 只需要方向鍵、Tab、Enter、Esc；不依賴 curses 或任何第三方套件。
"""
from __future__ import annotations
import colorsys
import shutil
import sys
import os

from ._compat import *
from .paths import *
from .colors import *
_cm = sys.modules[__package__ + ".colors"]
from .colorpicker import (
    _ITEM_LABEL_ZH,
    _TERMINAL_COLOR_KEYS,
    _xterm256_rgb,
    _normalize_terminal_color,
    _windows_swatch,
)

ESC = "\x1b"
RST = "\x1b[0m"


# ---------------------------------------------------------------- 終端控制
def _enable_vt() -> None:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for std in (-11, -12):
            handle = kernel32.GetStdHandle(std)
            mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _read_key() -> str:
    import msvcrt
    key = msvcrt.getwch()
    if key in ("\x00", "\xe0"):
        code = msvcrt.getwch()
        return {"H": "up", "P": "down", "K": "left", "M": "right",
                "I": "pgup", "Q": "pgdn", "G": "home", "O": "end", "\x0f": "btab"}.get(code, "")
    return {"\r": "enter", "\n": "enter", "\x1b": "esc", "\t": "tab", "\x03": "esc"}.get(key, key)


def _vlen(text: str) -> int:
    """可見寬度（略過 ANSI，全形算 2）。"""
    import re
    import unicodedata
    plain = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in plain)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_rgb(value: str):
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _contrast_fg(rgb) -> str:
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return "\x1b[38;2;0;0;0m" if lum > 140 else "\x1b[38;2;255;255;255m"


def _rgb_of(value: str):
    """任何顏色值 → 近似 RGB（供選取標記對比用）；REVERSE 回傳 None。"""
    try:
        if value.lower().startswith("bg:#"):
            return _hex_rgb(_normalize_terminal_color(value[3:]))
        if value.startswith("#"):
            return _hex_rgb(_normalize_terminal_color(value))
        if value.startswith(("COLOR_", "BG_")):
            return _xterm256_rgb(int(value.rsplit("_", 1)[1]))
        if value in _cm._BASIC_SWATCH_INDEX:
            return _xterm256_rgb(_cm._BASIC_SWATCH_INDEX[value])
    except Exception:
        pass
    return None


def _swatch(value: str, width: int = 4) -> str:
    """一塊實心色票（背景色）；RESET / REVERSE 以特殊樣式標示。"""
    if value == "REVERSE":
        return f"{ESC}[7m{' ' * width}{RST}"
    if value == "RESET":
        return f"{ESC}[100m{'╌' * width}{RST}"
    if value.startswith("#") or value.lower().startswith("bg:#"):
        try:
            r, g, b = _hex_rgb(_normalize_terminal_color(value[3:] if value.lower().startswith("bg:") else value))
            return f"{ESC}[48;2;{r};{g};{b}m{' ' * width}{RST}"
        except Exception:
            return " " * width
    base = _windows_swatch(value)
    # _windows_swatch 固定 4 格寬；需要其他寬度時重組
    return base if width == 4 else base.replace("    ", " " * width, 1)


# ---------------------------------------------------------------- 預覽
_SAMPLE_ROWS = [
    ["2026/08", "14 小時 20 分鐘", "3 小時 05 分鐘", "1 小時 10 分鐘"],
    ["2026/09", "7 小時 45 分鐘", "1 小時 30 分鐘", "0 小時 50 分鐘"],
]


def _preview_lines(work: dict) -> list[str]:
    from .commands.time_report import _render_time_rows
    month = datetime.now().strftime("%Y/%m")
    rows = [*_SAMPLE_ROWS, [month, "13 小時 02 分鐘", "2 小時 15 分鐘", "1 小時 40 分鐘"]]
    saved = (_cm._COLORS_CACHE, _cm._COLORS_CACHE_MTIME)
    try:
        mtime = COLORS_FILE.stat().st_mtime if COLORS_FILE.exists() else 0
    except Exception:
        mtime = 0
    _cm._COLORS_CACHE = dict(work)
    _cm._COLORS_CACHE_MTIME = mtime
    try:
        text = _render_time_rows(rows, "https://www.coolenglish.edu.tw/time/time_view_detail_by_people.php?id=1234", "Amy (amy@example.com)") or ""
    finally:
        _cm._COLORS_CACHE, _cm._COLORS_CACHE_MTIME = saved
    return [ln for ln in text.split("\n") if ln.strip()]


def _terminal_preview(work: dict) -> str:
    def val(key):
        v = work.get(key, DEFAULT_COLORS[key])
        try:
            return _hex_rgb(_normalize_terminal_color(v))
        except Exception:
            return _hex_rgb(DEFAULT_COLORS[key])
    bg, fg, cur = val("terminal_background_color"), val("terminal_text_color"), val("terminal_cursor_color")
    return (
        f"{ESC}[48;2;{bg[0]};{bg[1]};{bg[2]}m{ESC}[38;2;{fg[0]};{fg[1]};{fg[2]}m  cool> cool -t   學習時間 Sample 123 "
        f"{ESC}[38;2;{cur[0]};{cur[1]};{cur[2]}m▌{ESC}[48;2;{bg[0]};{bg[1]};{bg[2]}m   {RST}"
    )


# ---------------------------------------------------------------- 色票分頁
class _Page:
    def __init__(self, title: str, cells: list[str], cols: int, cell_w: int):
        self.title, self.cells, self.cols, self.cell_w = title, cells, max(1, cols), cell_w


def _hsl_cells(hues: int, lights, sat: float, prefix: str = "") -> list[str]:
    cells: list[str] = []
    for light in lights:
        for h in range(hues):
            r, g, b = colorsys.hls_to_rgb(h / hues, light, sat)
            cells.append(prefix + _rgb_to_hex(round(r * 255), round(g * 255), round(b * 255)))
    return cells


def _gray_cells(count: int, prefix: str = "") -> list[str]:
    return [prefix + _rgb_to_hex(*(round(255 * i / (count - 1)),) * 3) for i in range(count)]


def _build_pages(item: str, width: int) -> list[_Page]:
    usable = max(20, width - 2)
    pages: list[_Page] = []
    terminal = item in _TERMINAL_COLOR_KEYS
    wide = min(32, usable // 2)
    hues = 36 if usable >= 74 else 18
    lights9 = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.72, 0.84, 0.94)
    # 精選：20 個色系 × 12 個深淺（類似 Material / Tailwind 的色階）
    fam = 20 if usable >= 42 else 10
    tones = (0.96, 0.90, 0.82, 0.74, 0.66, 0.58, 0.50, 0.42, 0.34, 0.26, 0.18, 0.10)
    curated = _hsl_cells(fam, tones, 0.78) + _gray_cells(fam)
    vivid = _hsl_cells(hues, lights9, 0.90) + _gray_cells(hues)
    soft = _hsl_cells(hues, lights9, 0.45) + _gray_cells(hues)
    if not terminal:
        names = [n for n in BASE_NAMED] + ["REVERSE"]
        pages.append(_Page("常用 37 色", names, min(12, usable // 6), 6))
        pages.append(_Page("精選色階", curated, fam, 2))
        pages.append(_Page("鮮豔色相", vivid, hues, 2))
        pages.append(_Page("柔和色相", soft, hues, 2))
        pages.append(_Page("背景 色相", _hsl_cells(hues, lights9, 0.80, "bg:") + _gray_cells(hues, "bg:"), hues, 2))
        pages.append(_Page("256 前景", [f"COLOR_{i:03d}" for i in range(256)], wide, 2))
        pages.append(_Page("256 背景", [f"BG_{i:03d}" for i in range(256)], wide, 2))
    else:
        pages.append(_Page("鮮豔色相", vivid, hues, 2))
        pages.append(_Page("柔和色相", soft, hues, 2))
        pages.append(_Page("精選色階", curated, fam, 2))
        pages.append(_Page("256 色", [_rgb_to_hex(*_xterm256_rgb(i)) for i in range(256)], wide, 2))
    return pages


def _locate(pages: list[_Page], value: str):
    """依目前值找出起始分頁與格子。"""
    target = value
    if value.startswith("#"):
        try:
            target = _normalize_terminal_color(value)
        except Exception:
            pass
    for pi, page in enumerate(pages):
        if target in page.cells:
            return pi, page.cells.index(target)
    return 0, 0


def _describe(value: str) -> str:
    if value == "REVERSE":
        return "終端反色（前景／背景互換，隨終端配色）"
    if value.startswith("COLOR_"):
        return f"256 色前景 #{int(value[6:])}"
    if value.startswith("BG_"):
        return f"256 色背景 #{int(value[3:])}"
    if value.lower().startswith("bg:#"):
        return "自訂 HEX（背景色）"
    if value.startswith("#"):
        return "自訂 HEX（文字色）" if True else ""
    return "常用色"


def _sample_text(value: str) -> str:
    ansi = _resolve_ansi(value)
    return f"{ansi}範例文字 Sample 123{RST}" if ansi != RST else "範例文字 Sample 123"


# ---------------------------------------------------------------- 主畫面
def run_color_tui(colors: dict, start_item: str | None = None):
    """回傳本次變更清單 [(中文名, key, 原值, 新值)]。"""
    _enable_vt()
    keys = list(DEFAULT_COLORS.keys())
    saved = dict(colors)                      # 已儲存（磁碟）狀態
    work = dict(colors)                       # 目前畫面上的狀態（含未確認的試色）
    original = dict(colors)                   # 進入時的狀態，用來列出變更
    cur = keys.index(start_item) if start_item in keys else 0
    focus = "palette" if start_item in keys else "list"
    page_i, cell_i = 0, 0
    pages: list[_Page] = []
    message = ""
    hex_buffer: str | None = None

    def open_palette():
        nonlocal pages, page_i, cell_i, focus
        term = shutil.get_terminal_size((100, 30))
        pages = _build_pages(keys[cur], min(term.columns, 100))
        page_i, cell_i = _locate(pages, saved.get(keys[cur], DEFAULT_COLORS[keys[cur]]))
        focus = "palette"

    if focus == "palette":
        open_palette()

    def candidate() -> str:
        return pages[page_i].cells[cell_i]

    def draw():
        term = shutil.get_terminal_size((100, 30))
        width = min(term.columns, 100)
        height = term.lines
        out: list[str] = []
        key = keys[cur]
        # --- 標題列
        out.append(f"{ESC}[1;36m cool -c  顏色設定{RST}   {DIM}報表即時預覽 · Enter 儲存 · Esc 還原/離開{RST}")
        out.append(f"{DIM}{'─' * width}{RST}")
        # --- 預覽
        prev = _preview_lines(work)
        if focus == "palette":                         # 視窗太矮時只留預覽表格，優先保證色票看得到
            pg0 = pages[page_i]
            want = min((len(pg0.cells) + pg0.cols - 1) // pg0.cols, 8)
            budget = height - 11 - want
        else:
            budget = height - 18
        if budget < len(prev):
            prev = prev[-budget:] if budget >= 4 else []
        out.extend(prev)
        out.append(_terminal_preview(work))
        out.append(f"{DIM}{'─' * width}{RST}")
        used = len(out) + 3
        # --- 項目
        if focus == "list":
            for i, k in enumerate(keys):
                value = work.get(k, DEFAULT_COLORS[k])
                mark = f"{ESC}[7m" if i == cur else ""
                pointer = "▸" if i == cur else " "
                changed = "*" if value != saved.get(k) else " "
                group = "報表" if k not in _TERMINAL_COLOR_KEYS else "終端"
                label = _ITEM_LABEL_ZH.get(k, k)
                line = f" {pointer} {DIM if not mark else ''}{group}{RST}{mark} {label}{' ' * max(0, 8 - _vlen(label))}{RST}{mark} {_swatch(value, 4)}{mark} {value}{changed}{RST}"
                out.append(line)
            out.append("")
            out.append(f"{DIM} ↑↓ 選擇項目   Enter 開啟色票   r 還原此項預設   d 全部還原預設   Esc/q 離開{RST}")
        else:
            label = _ITEM_LABEL_ZH.get(key, key)
            desc = COLOR_DESCRIPTIONS.get(key, "")
            out.append(f" {ESC}[1m{label}{RST}  {DIM}{desc}{RST}   目前: {_swatch(saved.get(key, DEFAULT_COLORS[key]), 2)} {saved.get(key, DEFAULT_COLORS[key])}")
            # 分頁籤
            tabs = []
            for i, pg in enumerate(pages):
                tabs.append(f"{ESC}[7m {pg.title} {RST}" if i == page_i else f" {pg.title} ")
            tabs.append(f"{ESC}[7m HEX {RST}" if hex_buffer is not None else " HEX(h) ")
            out.append(" " + " ".join(tabs))
            pg = pages[page_i]
            rows_total = (len(pg.cells) + pg.cols - 1) // pg.cols
            avail = max(3, height - used - 6)
            cur_row = cell_i // pg.cols
            first = min(max(0, cur_row - avail + 1), max(0, rows_total - avail)) if rows_total > avail else 0
            for r in range(first, min(rows_total, first + avail)):
                line = " "
                for c in range(pg.cols):
                    idx = r * pg.cols + c
                    if idx >= len(pg.cells):
                        break
                    val = pg.cells[idx]
                    selected = idx == cell_i
                    if pg.cell_w == 6:
                        line += (f"{ESC}[1m[{RST}{_swatch(val, 4)}{ESC}[1m]{RST}" if selected else f" {_swatch(val, 4)} ")
                    else:
                        if selected:
                            rgb = _rgb_of(val)
                            fg = _contrast_fg(rgb) if rgb else ""
                            sw = _swatch(val, 2)
                            line += sw.replace("  ", f"{fg}◆ ", 1) if rgb else sw
                        else:
                            line += _swatch(val, 2)
                out.append(line)
            if rows_total > avail:
                out.append(f"{DIM} 第 {first + 1}-{min(rows_total, first + avail)} / {rows_total} 列（↑↓ 捲動）{RST}")
            val = work.get(key, DEFAULT_COLORS[key])
            out.append(f" 試色: {_swatch(val, 4)} {ESC}[1m{val}{RST}  {DIM}{_describe(val)}{RST}   {_sample_text(val) if key not in _TERMINAL_COLOR_KEYS else ''}")
            if hex_buffer is not None:
                out.append(f" 輸入 HEX（#RRGGBB，Enter 套用，Esc 取消）： {ESC}[1m#{hex_buffer}{RST}▌")
            else:
                out.append(f"{DIM} ←→↑↓ 移動   Tab 換頁   h 輸入 HEX   r 預設   Enter 儲存   Esc 取消{RST}")
        if message:
            out.append(f" {ESC}[33m{message}{RST}")
        # 單次輸出：游標歸位、逐行清尾、清掉剩餘畫面
        body = "\n".join(line + f"{ESC}[K" for line in out[:max(1, height - 1)])
        sys.stdout.write(f"{ESC}[H{body}{ESC}[J")
        sys.stdout.flush()

    def set_candidate():
        work[keys[cur]] = candidate()

    sys.stdout.write(f"{ESC}[?1049h{ESC}[?25l")
    sys.stdout.flush()
    try:
        while True:
            draw()
            k = _read_key()
            message = ""
            if hex_buffer is not None:                      # ---- HEX 輸入模式
                if k == "esc":
                    hex_buffer = None
                    work[keys[cur]] = saved.get(keys[cur], DEFAULT_COLORS[keys[cur]])
                elif k == "enter":
                    try:
                        normalized = _normalize_terminal_color("#" + hex_buffer)
                        work[keys[cur]] = normalized
                        hex_buffer = None
                        message = "已帶入 HEX，按 Enter 儲存"
                    except Exception:
                        message = "HEX 格式錯誤，請輸入 3 或 6 位 16 進位數字"
                elif k == "\x08" and hex_buffer:
                    hex_buffer = hex_buffer[:-1]
                elif len(k) == 1 and k in "0123456789abcdefABCDEF" and len(hex_buffer) < 6:
                    hex_buffer += k.lower()
                    if len(hex_buffer) in (3, 6):
                        try:
                            work[keys[cur]] = _normalize_terminal_color("#" + hex_buffer)
                        except Exception:
                            pass
                continue

            if focus == "list":
                if k == "up" and cur > 0:
                    cur -= 1
                elif k == "down" and cur < len(keys) - 1:
                    cur += 1
                elif k in ("home",):
                    cur = 0
                elif k in ("end",):
                    cur = len(keys) - 1
                elif k == "enter":
                    open_palette()
                    set_candidate()
                elif k in ("r", "R"):
                    key = keys[cur]
                    work[key] = DEFAULT_COLORS[key]
                    saved[key] = DEFAULT_COLORS[key]
                    colors.update(work)
                    save_colors(colors)
                    apply_terminal_colors()
                    message = f"已還原「{_ITEM_LABEL_ZH.get(key, key)}」為預設 {DEFAULT_COLORS[key]}"
                elif k in ("d", "D"):
                    for key in keys:
                        work[key] = DEFAULT_COLORS[key]
                        saved[key] = DEFAULT_COLORS[key]
                    colors.update(work)
                    save_colors(colors)
                    apply_terminal_colors()
                    message = "已全部還原為預設"
                elif k in ("esc", "q", "Q"):
                    break
                continue

            # ---- 色票模式
            pg = pages[page_i]
            if k == "left" and cell_i > 0:
                cell_i -= 1
            elif k == "right" and cell_i < len(pg.cells) - 1:
                cell_i += 1
            elif k == "up":
                cell_i = max(0, cell_i - pg.cols) if cell_i - pg.cols >= 0 else cell_i
            elif k == "down":
                cell_i = cell_i + pg.cols if cell_i + pg.cols < len(pg.cells) else cell_i
            elif k == "pgup":
                cell_i = max(0, cell_i - pg.cols * 4)
            elif k == "pgdn":
                cell_i = min(len(pg.cells) - 1, cell_i + pg.cols * 4)
            elif k in ("tab", "btab"):
                step = 1 if k == "tab" else -1
                old = candidate()
                page_i = (page_i + step) % len(pages)
                cell_i = min(cell_i, len(pages[page_i].cells) - 1)
                # 換頁時盡量停在同一個顏色
                if old in pages[page_i].cells:
                    cell_i = pages[page_i].cells.index(old)
            elif k in ("h", "H", "#"):
                hex_buffer = ""
                continue
            elif k in ("r", "R"):
                work[keys[cur]] = DEFAULT_COLORS[keys[cur]]
                continue
            elif k == "enter":
                key = keys[cur]
                value = candidate()
                if key in _TERMINAL_COLOR_KEYS:
                    try:
                        value = _normalize_terminal_color(value)
                    except ValueError as error:
                        message = str(error)
                        continue
                work[key] = value
                saved[key] = value
                colors[key] = value
                save_colors(colors)
                apply_terminal_colors()
                message = f"已儲存「{_ITEM_LABEL_ZH.get(key, key)}」= {value}"
                focus = "list"
                continue
            elif k == "esc":
                key = keys[cur]
                work[key] = saved.get(key, DEFAULT_COLORS[key])
                focus = "list"
                continue
            set_candidate()
    finally:
        sys.stdout.write(f"{ESC}[?25h{ESC}[?1049l")
        sys.stdout.flush()

    changes = []
    for key in keys:
        if original.get(key) != saved.get(key):
            changes.append((_ITEM_LABEL_ZH.get(key, key), key, original.get(key, DEFAULT_COLORS[key]), saved.get(key)))
    return changes


__all__ = ["run_color_tui"]
