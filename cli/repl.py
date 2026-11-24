"""Interactive cool> command loop."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *
from .security import *
from .accounts import *
from .terminal_input import *
from .lineedit import read_line
from .colorpicker import *
from .help import *
from .version import *
from .commands.account import *
from .commands.time_report import *
from .commands.urls import *
from .modifiers import MODIFIER_NAMES_RE, MODIFIERS, normalize_text, parse_modifiers
from .runner import run_with_modifiers, EXIT
from .dispatch import dispatch, HELP_FLAGS, SLASH_HELP, suggest

PROMPT = f"{CYAN}cool>{RESET} "
HISTORY_FILE = _BASE / ".cool_history"

_SLASH_WORDS = r"clear|cls|c|passwd|pwd|exit|quit|q|help|h|IG|INEEDLINK"

# `| /timer 5` 當成 `> /timer 5`（容錯：使用者常把修飾符接在 | 後面）
# 例外：後面接著 -h / --help 時是在查說明（`/clear | /at -h | /show -h`），仍然當成串接
_HELP_AHEAD = r"(?!\s+(?:-h|--help|/help)(?:\s|$|\|))"
_PIPE_MODIFIER = re.compile(rf"\|\s*(?=/(?:{MODIFIER_NAMES_RE})\b{_HELP_AHEAD})", re.IGNORECASE)

# 串接符號：`&&`；以及後面接著 cool / sudo / slash 指令的 `|`（`cool -g a|b` 的多選語法不受影響）
_CHAIN_SPLIT = re.compile(rf"(&&|;|\|(?=\s*(?:cool\b|sudo\b|/(?:{_SLASH_WORDS}|{MODIFIER_NAMES_RE})\b)))", re.IGNORECASE)

_EXIT = EXIT


def split_line(line: str) -> tuple[list[str], list[str]]:
    """把一行輸入切成 (各段指令, 段與段之間的符號)。"""
    line = _PIPE_MODIFIER.sub("> ", normalize_text(line))
    parts = _CHAIN_SPLIT.split(line)
    return [p.strip() for p in parts[0::2]], parts[1::2]


# ───────────── 括號群組 ─────────────
# (A | B | C) 把同一個設定「分配」給多個東西，或讓一組指令當成一個單位：
#   -h > (/show | /at | /repeat)         → -h /show | -h /at | -h /repeat（查多個說明）
#   (cool -t | cool -a) > /timer 5       → cool -t > /timer 5 | cool -a > /timer 5
#   (cool -t | cool -a) > (/timer 5 | /timer 9)   兩邊相乘
#   cool -t && (cool -c | cool -a)       單獨的括號 = 一個單位（運算優先順序）
# 只有出現在「新運算元開始處」（行首，或 > | ; & ( 之後）的 ( 才算群組，所以參數裡的普通括號不受影響。
_PH = re.compile(r"\x00(\d+)\x00")
_MAX_DEPTH = 8
_depth = 0


def extract_groups(line: str):
    """把最外層的括號群組換成佔位符。回傳 (文字, 群組內容清單, 錯誤訊息或 None)。"""
    out: list[str] = []
    groups: list[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        prev = "".join(out).rstrip()[-1:] if out else ""
        if ch == "(" and (not prev or prev in ">|;&("):
            depth, j = 1, i + 1
            while j < n and depth:
                depth += (line[j] == "(") - (line[j] == ")")
                j += 1
            if depth:
                return None, None, "括號沒有成對，整行都沒有執行。"
            groups.append(line[i + 1:j - 1])
            out.append(f"\x00{len(groups) - 1}\x00")
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out), groups, None


def split_items(raw: str) -> list[str]:
    """括號內用 | 或 ; 分隔的項目（巢狀括號內的分隔符不算）。"""
    items, buf, depth = [], [], 0
    for ch in raw:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and ch in "|;":
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf).strip())
    return [x for x in items if x]


def _side(text: str, groups: list[str]):
    """> 的一側：純群組 → (項目清單, True)；純文字 → ([文字], False)；其他 → None。"""
    t = text.strip()
    m = re.fullmatch(r"\x00(\d+)\x00", t)
    if m:
        items = split_items(groups[int(m.group(1))])
        return (items, True) if items else None
    if not t or _PH.search(t):
        return None
    return [t], False


def _combine(left: str, right: str, right_is_group: bool) -> str:
    lt = left.split()
    if right_is_group and lt and lt[-1] in HELP_FLAGS:
        return f"{left} {right}"            # -h > (/show | /at) → -h /show：括號裡是說明主題
    if ">" in left:
        return f"{left} {right}"            # 已經有 > 了，繼續往後附加
    return f"{left} > {right}"


def _run_with_groups(mgr, seg: str, groups: list[str]):
    """執行含括號群組的一段指令。"""
    if not _PH.search(seg):
        return _run_segment(mgr, seg)
    m = re.fullmatch(r"\s*\x00(\d+)\x00\s*", seg)
    if m:                                                    # 單獨的括號：當成一個單位
        return run_line(mgr, groups[int(m.group(1))])
    left, sep, right = seg.partition(">")
    if not sep:
        note("WARN", "括號要單獨成一段，或接在 > 的左右，例如：-h > (/show | /at)、(cool -t | cool -a) > /timer 5")
        return False
    ls, rs = _side(left, groups), _side(right, groups)
    if any(_PH.fullmatch(x.strip()) and not split_items(groups[int(_PH.fullmatch(x.strip()).group(1))]) for x in (left, right)):
        note("WARN", "括號裡是空的，整行都沒有執行。")
        return False
    if ls is None or rs is None:
        note("WARN", "> 的每一側要嘛是一個完整的括號群組，要嘛是一般文字，例如：cool -t > (/timer 5 | /timer 9)")
        return False
    lefts, _ = ls
    rights, right_is_group = rs
    total = len(lefts) * len(rights)
    if total > 50:
        note("WARN", f"展開後有 {total} 個指令，超過上限 50，整行都沒有執行。")
        return False
    for l in lefts:
        for r in rights:
            if run_line(mgr, _combine(l, r, right_is_group)) is _EXIT:
                return _EXIT
    return True


_SLASH_NAMES = ("clear", "cls", "c", "passwd", "pwd", "exit", "quit", "q", "help", "h", "IG", "INEEDLINK")


def _run_slash(mgr: AccountManager, seg: str):
    """slash 指令可以帶修飾符：/clear > /timer 5 = 5 秒後清畫面（slash 指令一瞬間就做完，/timer 視為等待時間）。"""
    tokens = seg.split()
    rest = tokens[1:]
    if ">" in seg or any(t.startswith("/") and t[1:].split("=")[0].lower() in MODIFIERS for t in rest):
        head, mods = parse_modifiers(rest, command=tokens[0], command_key="slash")
        if not mods.ok:
            return False
        if mods.timer and mods.delay is None and mods.at is None:
            mods.delay, mods.timer = mods.timer, None
        return run_with_modifiers(mods, lambda: _slash_core(mgr, " ".join([tokens[0], *head])))
    return _slash_core(mgr, seg)


def _slash_core(mgr: AccountManager, seg: str):
    """/clear /passwd /exit /help /IG /INEEDLINK。"""
    parts = seg[1:].split()
    if not parts:
        return True
    # 字母被空白拆開（/c l e a r）：合起來若是已知指令就當成它
    if len(parts) > 1 and all(len(x) == 1 for x in parts) and "".join(parts) in _SLASH_NAMES:
        note("INFO", f"已當成 /{''.join(parts)} 執行。")
        parts = ["".join(parts)]
    raw = "/" + parts[0]
    args = parts[1:]
    cmd = parts[0]
    if any(a in HELP_FLAGS for a in args):
        key = SLASH_HELP.get(cmd.lower())
        if key and key in CMD_HELP:
            print(CMD_HELP[key])
            return True
    if not args and raw == "/IG":
        print("製作者IG：c.pls._")
        print("https://www.instagram.com/c.pls._/")
        return True
    if not args and raw == "/INEEDLINK":
        print("連結收藏：")
        print("https://docs.google.com/document/d/14c3QKaOBrai301l9r5-XlVf2EXsO9io-mFBwQ-K7djo/edit?usp=sharing")
        return True
    helped = any(a in HELP_FLAGS for a in args)
    if cmd in ("exit", "quit", "q"):
        if helped:
            print(CMD_HELP["exit"])
            return True
        note("INFO", "再見。")
        return _EXIT
    if cmd in ("clear", "cls", "c"):
        if helped:
            print(CMD_HELP["clear"])
            return True
        try:
            subprocess.run(["clear" if os.name != "nt" else "cls"], shell=False)
        except Exception:
            os.system("clear" if os.name != "nt" else "cls")
        return True
    if cmd in ("passwd", "pwd"):
        if helped:
            print(CMD_HELP["passwd"])
            return True
        cmd_passwd(mgr, args)
        return True
    if cmd in ("help", "h"):
        print(HELP_TEXT)
        return True
    if cmd.lower() in MODIFIERS:
        note("WARN", f"/{cmd} 是附加設定，要接在指令後面，例如：cool -g > /timer 1:30:00、cool -l > /show")
        return False
    hint = suggest(cmd, _SLASH_NAMES)
    extra = f"，你是不是要 /{hint}？" if hint else ""
    note("WARN", f"未知 slash 指令：{raw}（可用 /clear /passwd /exit /help{extra}）")
    return False


def _run_segment(mgr: AccountManager, seg: str):
    """執行一段指令。回傳 True/False，或 _EXIT 表示要離開 cool>。"""
    seg = seg.strip()
    if not seg:
        return True
    if seg.startswith(">"):
        note("WARN", "`>` 前面要先有指令，例如：cool -g > /timer 1:30:00")
        return False
    if seg.startswith("/"):
        return _run_slash(mgr, seg)

    words = seg.split()
    first = words[0].lower()
    if words[0].startswith("-") or first in ("passwd", "--passwd"):
        words = ["cool"] + words                  # 可以省略 cool：`-h > (/show | /at)`、`-t && -g a`
        first = "cool"

    if first == "sudo":
        rest = words[1:]
        if any(a in HELP_FLAGS for a in rest):
            print(CMD_HELP["sudo"])
            return True
        if rest and rest[0].lower() == "cool":
            rest = rest[1:]
        if not rest:
            if has_sudo():
                note("INFO", "已取得 cool sudo 權限")
            return True
        if rest[0].startswith("/"):
            if not has_sudo():
                return False
            return _run_slash(mgr, " ".join(rest))
        if not rest[0].startswith("-") and rest[0] not in ("passwd", "--passwd"):
            note("WARN", f"未知 sudo 用法：sudo {' '.join(words[1:])}（可用 sudo / sudo cool -l / sudo /passwd）")
            return False
        if not has_sudo():
            return False
        return dispatch(mgr, rest)

    if first == "cool":
        rest = words[1:]
        if rest and rest[0].lower() == "cool":
            rest = rest[1:]
        if not rest:
            note("WARN", "請輸入參數，例如 cool -h / cool --help")
            return False
        if rest[0].lower() == "sudo":
            return _run_segment(mgr, "sudo cool " + " ".join(rest[1:]))
        if rest[0].startswith("/") and rest[0][1:].lower() in SLASH_HELP:
            return _run_slash(mgr, " ".join(rest))          # cool /timer -h、cool /clear
        if not rest[0].startswith("-") and rest[0] not in ("passwd", "--passwd"):
            note("WARN", f"參數需以 - 開頭，例如 cool -h，收到：{rest[0]}")
            return False
        return dispatch(mgr, rest)

    note("WARN", f"未知指令：{seg}（dash 參數需以 cool 開頭，例如 cool -h；slash 指令用 /clear /passwd /exit）")
    return False


def run_line(mgr: AccountManager, line: str):
    """執行一整行（可含 && / | 串接）。回傳 _EXIT 表示要離開 cool>。"""
    global _depth
    if _depth >= _MAX_DEPTH:
        note("WARN", "括號巢狀太深，已停止。")
        return False
    text, groups, err = extract_groups(normalize_text(line))
    if err:
        note("WARN", err)
        return True
    segments, ops = split_line(text)
    if len(segments) > 1 and any(not x for x in segments):
        note("WARN", f"串接符號（{' '.join(dict.fromkeys(ops))}）旁邊缺少指令，整行都沒有執行。")
        return True
    stopped = False
    for i, segment in enumerate(segments):
        if i > 0 and ops[i - 1] == "&&" and stopped:
            continue                      # && 前一個失敗 → 跳過這段（遇到 | 才重新開始）
        _depth += 1
        try:
            result = _run_with_groups(mgr, segment, groups)
        finally:
            _depth -= 1
        if result is _EXIT:
            return _EXIT
        stopped = not result
    return True


def repl(mgr: AccountManager):
    while True:
        try:
            line = _strip_control_sequences(read_line(PROMPT))
        except (EOFError, KeyboardInterrupt):
            print()
            note("INFO", "再見。")
            break
        if not line:
            continue
        reset_sudo()
        if run_line(mgr, line) is _EXIT:
            break

__all__ = [name for name in globals() if not name.startswith("__")]
