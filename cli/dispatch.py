"""cool 指令的統一分派：互動模式（cool>）、單行模式（cool.py -g ...）、串接（&& / |）都走這裡。

分派流程：正規化輸入 → 解析 `>` 與 /修飾符 → 依修飾符執行（等待 / 重複 / 時限 / 清畫面）→ 指令本體。
「顯示說明」也是指令本體之一，所以 `cool -h > /timer 5 /clear`（顯示 5 秒再清掉）一樣成立。
新增指令只要在 _ALIASES 加一列；新增修飾符請看 modifiers.py。
"""
from __future__ import annotations
import difflib
from ._compat import *
from .colors import *
from .help import *
from .version import *
from .modifiers import parse_modifiers, set_current, normalize_text, MODIFIERS
from .runner import run_with_modifiers
from .colorpicker import *
from .commands.account import *
from .commands.time_report import *
from .commands.urls import *
from .security import *

HELP_FLAGS = ("-h", "--help", "/help")

# 指令別名 → (說明鍵, 內部名稱)
_ALIASES: dict[str, tuple[str, str]] = {
    "-l": ("login", "login"), "--login": ("login", "login"),
    "-a": ("account", "account"), "--account": ("account", "account"), "--acc": ("account", "account"),
    "-g": ("go", "go"), "--go": ("go", "go"),
    "-u": ("url", "url"), "--url": ("url", "url"), "--visit": ("url", "url"),
    "-t": ("time", "time"), "--time": ("time", "time"),
    "-n": ("name", "name"), "--name": ("name", "name"), "--rename": ("name", "name"),
    "-c": ("color", "color"), "--color": ("color", "color"), "--colour": ("color", "color"), "--colors": ("color", "color"),
    "-A": ("all", "all"), "--ALL": ("all", "all"),
    "-H": ("hidden", "hidden"),
    "-h": ("help", "help"), "--help": ("help", "help"),
    "-v": ("version", "version"), "--version": ("version", "version"),
    "passwd": ("passwd", "passwd"), "--passwd": ("passwd", "passwd"),
}

# 說明查詢：cool -h /timer、cool /timer -h 都能看到對應說明
_HELP_WORDS = {"/show": "show", "/timer": "timer", "/for": "timer", "/delay": "delay", "/at": "at", "/repeat": "repeat",
               "/clear": "clear", "/cls": "clear", "/exit": "exit", "/quit": "exit", "/q": "exit",
               "/passwd": "passwd", "/pwd": "passwd", "/ig": "ig", "/ineedlink": "ineedlink",
               "&&": "chain", "|": "chain", ";": "chain", "sudo": "sudo", ">": "mod", "group": "group", "()": "group"}
# slash 指令（不帶 / 的名稱）→ 說明鍵；repl 的 /xxx -h 與 cool /xxx -h 共用
SLASH_HELP = {k[1:]: v for k, v in _HELP_WORDS.items() if k.startswith("/")}
SLASH_HELP.update({"help": "help", "h": "help", "c": "clear"})


def help_key_for(words: list[str]) -> str:
    """從參數找出該顯示哪一段說明；找不到回傳空字串（顯示總說明）。只看第一個 `>` 之前的字。"""
    if ">" in words:
        words = words[:words.index(">")]
    if any(w in ("-u", "--url", "--visit") for w in words) and any(w in ("-w", "--write", "write") for w in words):
        return "write"
    for w in words:
        # 單字母旗標分大小寫（-A ≠ -a、-H ≠ -h）；--long 與 /slash 不分大小寫
        lw = w if (w in _ALIASES or (w.startswith("-") and not w.startswith("--"))) else w.lower()
        if lw in _ALIASES and _ALIASES[lw][0] not in ("", "help"):
            return _ALIASES[lw][0]
        if lw in _HELP_WORDS:
            return _HELP_WORDS[lw]
    return ""


def suggest(word: str, candidates) -> str:
    """打錯字的建議：先看大小寫寫反（-G → -g），再看相似度。"""
    cands = list(candidates)
    for c in cands:
        if c.lower() == word.lower() and c != word:
            return c
    m = difflib.get_close_matches(word, cands, n=1, cutoff=0.7)
    return m[0] if m else ""


def _invoke(mgr, kind: str, args: list[str]) -> bool:
    if kind == "login":
        cmd_login(mgr, args)
    elif kind == "account":
        cmd_account(mgr, args)
    elif kind == "go":
        cmd_go(mgr, args)
    elif kind == "url":
        cmd_url(mgr, args)
    elif kind == "time":
        cmd_time(mgr, args)
    elif kind == "name":
        cmd_name(mgr, args)
    elif kind == "color":
        if args and args[0].lower() in ("--color", "--colour", "--colors"):
            args = args[1:]
        cmd_color(mgr, args)
    elif kind == "all":
        cmd_show(mgr)
    elif kind == "passwd":
        cmd_passwd(mgr, args)
    elif kind == "help":
        print(HELP_TEXT)
    elif kind == "version":
        print(VERSION)
    elif kind == "hidden":
        print("  /IG                         顯示製作者 IG 名稱與主頁面")
        print("  /INEEDLINK                  顯示所有課程連結")
    return True


def dispatch(mgr, words: list[str]) -> bool:
    """執行一個 cool 指令。words 已去掉開頭的 cool / sudo，例如 ['-g', 'a', '>', '/timer', '5']。

    回傳 True = 成功（或依 /timer 設定的時間到而正常結束），False = 失敗或被使用者取消。
    """
    words = [normalize_text(w) for w in words]
    if not words:
        note("WARN", "請輸入參數，例如 cool -h")
        return False
    raw = words[0]
    rest = words[1:]

    if raw in ("-s", "--show"):
        note("WARN", "-s 已改為 /show，例如：cool -l /show、cool -g > /show")
        return False

    # cool -h /timer：只想看某個修飾符的說明（沒有 `>`）
    if ">" not in words and any(w in HELP_FLAGS for w in words):
        key = help_key_for([w for w in words if w not in HELP_FLAGS])
        if key:
            print(CMD_HELP[key])
            return True

    entry = _ALIASES.get(raw)
    if entry is None:
        if raw.startswith(">"):
            note("WARN", "`>` 前面要先有指令，例如：cool -g > /timer 1:30:00")
            return False
        hint = suggest(raw, _ALIASES)
        extra = f"，你是不是要 cool {hint}？" if hint else ""
        note("WARN", f"未知指令：{raw}（輸入 cool -h 查看{extra}）")
        return False
    key, kind = entry

    label = f"cool {raw}"
    args, mods = parse_modifiers(rest, command=label, command_key=kind)
    if not mods.ok:
        return False

    helping = raw in HELP_FLAGS or any(a in HELP_FLAGS for a in args)

    def once() -> bool:
        set_current(mods)
        try:
            if helping:
                if raw in HELP_FLAGS:
                    hk = help_key_for(args) or ("help" if any(a in HELP_FLAGS for a in args) else "")
                else:
                    hk = help_key_for([raw] + args)
                print(CMD_HELP[hk] if hk in CMD_HELP else HELP_TEXT)
                return True
            return _invoke(mgr, kind, args)
        finally:
            set_current(None)

    # cool -g 的 /timer 是「瀏覽器開多久」，由 cmd_go 自己處理
    # 只輸出資料、不需要互動的指令：/timer 當成「計時視窗」，時間走完才返回（互動型指令做完就直接結束）
    hold = helping or kind in ("help", "version", "hidden", "all", "time")
    return run_with_modifiers(mods, once, own_timer=(kind == "go" and not helping), hold=hold)


__all__ = ["dispatch", "help_key_for", "suggest", "HELP_FLAGS", "SLASH_HELP"]
