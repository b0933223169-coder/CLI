"""ANSI color definitions, persistence, and console presentation helpers."""
from __future__ import annotations
from ._compat import *
from .paths import *

GREEN, RED, YELLOW, BLUE, CYAN, MAGENTA, DIM, RESET = (
    "\033[1;32m", "\033[1;31m", "\033[1;33m",
    "\033[1;34m", "\033[1;36m", "\033[1;35m", "\033[2m", "\033[0m",
)
BOLD = "\033[1m"
REVERSE = "\033[7m"
RED_BG = "\033[41m"
WHITE = "\033[1;37m"
RED_BG_WHITE = "\033[41;97m"

ANS_MEM = None

BASE_NAMED = {
    "GREEN": GREEN, "RED": RED, "YELLOW": YELLOW, "BLUE": BLUE,
    "CYAN": CYAN, "MAGENTA": MAGENTA, "WHITE": WHITE, "DIM": DIM, "RESET": RESET,
    "RED_BG": RED_BG, "RED_BG_WHITE": RED_BG_WHITE,
    "YELLOW_BG_WHITE": "\033[43;97m", "BLUE_BG_WHITE": "\033[44;97m",
    "MAGENTA_BG_WHITE": "\033[45;97m", "CYAN_BG_WHITE": "\033[46;97m",
    "GREEN_BG_WHITE": "\033[42;97m",
    "ORANGE": "\033[38;5;208m", "ORANGE_BG": "\033[48;5;208m",
    "PURPLE": "\033[38;5;135m", "PURPLE_BG": "\033[48;5;135m",
    "PINK": "\033[38;5;213m", "PINK_BG": "\033[48;5;213m",
    "LIME": "\033[38;5;154m", "LIME_BG": "\033[48;5;154m",
    "TEAL": "\033[38;5;37m", "TEAL_BG": "\033[48;5;37m",
    "GOLD": "\033[38;5;220m", "GOLD_BG": "\033[48;5;220m",
    "SKY": "\033[38;5;117m", "SKY_BG": "\033[48;5;117m",
    "BROWN": "\033[38;5;130m", "BROWN_BG": "\033[48;5;130m",
    "GRAY": "\033[38;5;245m", "GRAY_BG": "\033[48;5;245m",
    "BLACK": "\033[38;5;16m", "BLACK_BG": "\033[48;5;16m",
}
# REVERSE 不放進 BASE_NAMED 的一般清單裡——它不是固定顏色，而是把「目前終端
# 的前景/背景」互換（SGR 7），所以特別另外處理：畫面上會被放在整個色盤網格
# 的最後面，獨立一整列、用完整名稱標示，而不是跟其他色塊擠在同一格裡。
AVAILABLE_COLORS_REVERSE_KEY = "REVERSE"

# 部分名稱在網格裡顯示的短標籤跟 key 不同（方便辨識，尤其是「終端反色」）
DISPLAY_LABEL = {"REVERSE": "終端反色"}
DISPLAY_LABEL_FULL = {"REVERSE": "終端反色（REVERSE，跟隨終端目前配色自動反相）"}

# 純前景色（不含背景）的名稱在色塊預覽時看不到顏色，所以另外準備一份
# 「預覽用背景色」對照表，跟實際套用的 ANSI 碼分開，只用來畫色塊。
_BASIC_FG_TO_BG = {
    "\033[1;32m": "\033[42m", "\033[1;31m": "\033[41m", "\033[1;33m": "\033[43m",
    "\033[1;34m": "\033[44m", "\033[1;36m": "\033[46m", "\033[1;35m": "\033[45m",
    "\033[1;37m": "\033[47m",
}
BASE_NAMED_SWATCH = {
    "GREEN": "\033[42m", "RED": "\033[41m", "YELLOW": "\033[43m", "BLUE": "\033[44m",
    "CYAN": "\033[46m", "MAGENTA": "\033[45m", "WHITE": "\033[47m",
    "DIM": "\033[100m", "RESET": "\033[49m", "REVERSE": "\033[7m",
    "RED_BG": "\033[41m", "RED_BG_WHITE": "\033[41m",
    "YELLOW_BG_WHITE": "\033[43m", "BLUE_BG_WHITE": "\033[44m",
    "MAGENTA_BG_WHITE": "\033[45m", "CYAN_BG_WHITE": "\033[46m",
    "GREEN_BG_WHITE": "\033[42m",
    "ORANGE": "\033[48;5;208m", "ORANGE_BG": "\033[48;5;208m",
    "PURPLE": "\033[48;5;135m", "PURPLE_BG": "\033[48;5;135m",
    "PINK": "\033[48;5;213m", "PINK_BG": "\033[48;5;213m",
    "LIME": "\033[48;5;154m", "LIME_BG": "\033[48;5;154m",
    "TEAL": "\033[48;5;37m", "TEAL_BG": "\033[48;5;37m",
    "GOLD": "\033[48;5;220m", "GOLD_BG": "\033[48;5;220m",
    "SKY": "\033[48;5;117m", "SKY_BG": "\033[48;5;117m",
    "BROWN": "\033[48;5;130m", "BROWN_BG": "\033[48;5;130m",
    "GRAY": "\033[48;5;245m", "GRAY_BG": "\033[48;5;245m",
    "BLACK": "\033[48;5;16m", "BLACK_BG": "\033[48;5;16m",
}

AVAILABLE_COLORS = dict(BASE_NAMED)
AVAILABLE_COLORS["REVERSE"] = REVERSE
for _i in range(256):
    AVAILABLE_COLORS[f"COLOR_{_i:03d}"] = f"\033[38;5;{_i}m"
    AVAILABLE_COLORS[f"BG_{_i:03d}"] = f"\033[48;5;{_i}m"

_BASIC_SWATCH_INDEX = {
    "GREEN": 2, "RED": 1, "YELLOW": 3, "BLUE": 4, "CYAN": 6, "MAGENTA": 5, "WHITE": 7,
    "DIM": 8, "RED_BG": 1, "RED_BG_WHITE": 1, "YELLOW_BG_WHITE": 3, "BLUE_BG_WHITE": 4,
    "MAGENTA_BG_WHITE": 5, "CYAN_BG_WHITE": 6, "GREEN_BG_WHITE": 2,
    "ORANGE": 208, "ORANGE_BG": 208, "PURPLE": 135, "PURPLE_BG": 135,
    "PINK": 213, "PINK_BG": 213, "LIME": 154, "LIME_BG": 154,
    "TEAL": 37, "TEAL_BG": 37, "GOLD": 220, "GOLD_BG": 220,
    "SKY": 117, "SKY_BG": 117, "BROWN": 130, "BROWN_BG": 130,
    "GRAY": 245, "GRAY_BG": 245, "BLACK": 16, "BLACK_BG": 16,
}

def _swatch_ansi(name_or_hex):
    """回傳『色塊預覽』專用的背景色 ANSI，跟實際套用值分開，
    確保像 WHITE/DIM/RESET 這種純前景或純樣式的項目也看得到色塊。"""
    if name_or_hex in BASE_NAMED_SWATCH:
        return BASE_NAMED_SWATCH[name_or_hex]
    if isinstance(name_or_hex, str):
        if name_or_hex.startswith("COLOR_") or name_or_hex.startswith("BG_"):
            idx = int(name_or_hex.rsplit("_", 1)[1])
            return f"\033[48;5;{idx}m"
        if name_or_hex.startswith("#"):
            hexcode = _hex_to_ansi(name_or_hex, bg=True)
            if hexcode:
                return hexcode
    return "\033[49m"

def _swatch_kind(name_or_hex):
    """給 curses 畫格子用：curses 不能跟 print() 出來的原始 ANSI 混用。
    回傳 ("reverse", None) / ("index", 0-255 的 xterm 色碼) / ("default", None)"""
    if name_or_hex == "REVERSE":
        return ("reverse", None)
    if isinstance(name_or_hex, str):
        if name_or_hex.startswith("COLOR_") or name_or_hex.startswith("BG_"):
            return ("index", int(name_or_hex.rsplit("_", 1)[1]))
        if name_or_hex in _BASIC_SWATCH_INDEX:
            return ("index", _BASIC_SWATCH_INDEX[name_or_hex])
    return ("default", None)

def _hex_to_ansi(hex_str: str, bg: bool = False) -> str | None:
    try:
        if not isinstance(hex_str, str):
            return None
        h = hex_str.strip().lstrip("#")
        if len(h) == 3:
            if not all(c in "0123456789abcdefABCDEF" for c in h):
                return None
            h = "".join(c*2 for c in h)
        if len(h) != 6:
            return None
        if not all(c in "0123456789abcdefABCDEF" for c in h):
            return None
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            return None
        return f"\033[{48 if bg else 38};2;{r};{g};{b}m"
    except Exception:
        return None

DEFAULT_COLORS = {
    "title": "MAGENTA", "title_text": "WHITE", "header": "CYAN",
    "cur": "REVERSE", "low": "RED_BG_WHITE", "url": "DIM", "sep": "DIM",
}
COLOR_DESCRIPTIONS = {
    "title": "標題外框 ┏━┓", "title_text": "標題文字 學習時間 - 116電機 ...",
    "header": "表頭 學習月份/停留平台時間", "cur": "當月已達標 反色高亮 ▶",
    "low": "未達標 紅底白字", "url": "網址列 https://...", "sep": "分隔線 ─ / -",
}

_COLORS_CACHE = None
_COLORS_CACHE_MTIME = 0

def load_colors() -> dict:
    global _COLORS_CACHE, _COLORS_CACHE_MTIME
    try:
        mtime = COLORS_FILE.stat().st_mtime if COLORS_FILE.exists() else 0
        if _COLORS_CACHE is not None and mtime == _COLORS_CACHE_MTIME:
            return _COLORS_CACHE.copy()
    except Exception:
        pass
    if COLORS_FILE.exists():
        try:
            data = json.loads(COLORS_FILE.read_text(encoding="utf-8"))
            out = DEFAULT_COLORS.copy()
            for k, v in data.items():
                if k in DEFAULT_COLORS and (v in AVAILABLE_COLORS or (isinstance(v, str) and v.startswith("#") and _hex_to_ansi(v) is not None)):
                    out[k] = v
            _COLORS_CACHE = out.copy()
            try:
                _COLORS_CACHE_MTIME = COLORS_FILE.stat().st_mtime
            except Exception:
                _COLORS_CACHE_MTIME = 0
            return out
        except Exception:
            pass
    _COLORS_CACHE = DEFAULT_COLORS.copy()
    _COLORS_CACHE_MTIME = 0
    return DEFAULT_COLORS.copy()

def save_colors(colors: dict):
    global _COLORS_CACHE, _COLORS_CACHE_MTIME
    data = json.dumps(colors, ensure_ascii=False, indent=2)
    _atomic_write(COLORS_FILE, data, 0o600)
    _COLORS_CACHE = colors.copy()
    try:
        _COLORS_CACHE_MTIME = COLORS_FILE.stat().st_mtime
    except Exception:
        _COLORS_CACHE_MTIME = 0

def _resolve_ansi(name: str) -> str:
    if not isinstance(name, str):
        return RESET
    if name.startswith("#"):
        ansi = _hex_to_ansi(name)
        return ansi if ansi else RESET
    if name in AVAILABLE_COLORS:
        return AVAILABLE_COLORS[name]
    return RESET

def get_color(key: str) -> str:
    colors = load_colors()
    name = colors.get(key, DEFAULT_COLORS.get(key, "RESET"))
    return _resolve_ansi(name)

def _color_preview_block(name: str) -> str:
    ansi = _resolve_ansi(name)
    if ansi == RESET:
        return f"████{RESET}"
    return f"{ansi}████{RESET}"

def _apply_color(key: str, text: str) -> str:
    return f"{get_color(key)}{text}{RESET}"

def _animate_rainbow_note(key: str):
    return

TAG_COLORS = {
    "OK": GREEN, "DONE": GREEN, "INFO": BLUE, "DEBUG": BLUE,
    "NOTICE": MAGENTA, "DEPEND": YELLOW, "SKIP": YELLOW, "WARN": YELLOW,
    "WORK": CYAN, "BUSY": CYAN, "FAILED": RED, "ERR": RED, "CRIT": RED, "ALERT": RED, "EMERG": RED,
}
TAG_WIDTH = 6

def display_width(s: str) -> int:
    import unicodedata
    try:
        if not isinstance(s, str):
            s = str(s)
        return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)
    except Exception:
        return len(s) if isinstance(s, str) else 0

def status_line(label: str, tag: str):
    color = TAG_COLORS.get(tag, RESET)
    try:
        dots = "." * max(2, 52 - display_width(label))
    except Exception:
        dots = ".."
    try:
        print(f"{label} {dots} [{color}{tag.center(TAG_WIDTH)}{RESET}]", flush=True)
    except Exception:
        print(f"{label} ... [{tag}]")

def note(tag: str, msg: str):
    color = TAG_COLORS.get(tag, RESET)
    try:
        print(f"{color}[{tag.center(TAG_WIDTH)}]{RESET} {msg}", flush=True)
    except Exception:
        try:
            print(f"[{tag.center(TAG_WIDTH)}] {msg}")
        except Exception:
            pass

__all__ = [name for name in globals() if not name.startswith("__")]
