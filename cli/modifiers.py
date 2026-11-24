"""指令修飾符：`>` 把設定附加給前面的指令。

  cool -g a|b > /timer 1:30:00        開啟連結組，90 分鐘後自動關閉瀏覽器
  cool -l > /show                      登入時顯示瀏覽器（取代舊的 -s）
  cool -c > /timer 30                  色彩選單最多開 30 秒，超過自動關閉
  cool -t > /delay 10:00               10 分鐘後才開始執行
  cool -g > /at 21:30 /timer 1:00:00   晚上 9:30 開始，跑 1 小時
  cool -t > /repeat 3                  連續執行 3 次

修飾符表（MODIFIERS）是唯一的定義處：要新增修飾符，只要在表裡加一列、
並在 runner.py 的 run_with_modifiers() 實作它的行為即可，解析、說明、錯誤提示都共用。

`>` 之後的每一個 /名稱 都是附加給「前面那個指令」的設定；寫在指令後面但沒有 `>` 也可以。
注意：在 cmd / PowerShell 等外層 shell 直接輸入時，`>` 會被 shell 當成輸出導向；
在 cool> 提示符下、桌面應用程式、或加引號時則沒有這個問題。
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from ._compat import *
from .colors import *


@dataclass
class Modifiers:
    show: bool = False
    timer: Optional[int] = None          # 最長執行時間（秒）；-g 則是瀏覽器開啟的時間
    delay: Optional[int] = None          # 先等待幾秒再執行
    at: Optional[str] = None             # 原始 HH:MM[:SS]，由 runner 換算成等待秒數
    repeat: int = 1                      # 連續執行次數
    clear: bool = False                  # 指令結束後清除畫面
    exit: bool = False                   # 指令結束後離開 cool
    given: list[str] = field(default_factory=list)   # 使用者實際寫了哪些修飾符
    ok: bool = True                      # False = 有錯誤，呼叫端應中止

    def any(self) -> bool:
        return bool(self.given)


# 修飾符定義：名稱 → (是否需要值, 可搭配的指令（None = 全部）, 說明)
MODIFIERS: dict[str, tuple[bool, Optional[tuple[str, ...]], str]] = {
    "show":   (False, ("login", "go"), "顯示瀏覽器視窗"),
    "timer":  (True,  None,            "最長執行時間，超過自動中止（-g 則為瀏覽器開啟的時間）"),
    "delay":  (True,  None,            "等待指定時間後才開始執行"),
    "at":     (True,  None,            "到指定時刻（時:分[:秒]）才開始執行"),
    "repeat": (True,  None,            "連續執行 N 次"),
    "exit":   (False, None,            "指令結束後離開 cool（可接在 /timer、/clear 之後）"),
    "clear":  (False, None,            "指令結束後清除畫面（搭配 /timer 時，畫面會保留到時間到再清）"),
}

# 把 `| /timer ...` 當成 `> /timer ...` 的寫法（容錯）
ALIASES = {"for": "timer"}
MODIFIER_NAMES_RE = "|".join([*MODIFIERS, *ALIASES])


MAX_SECONDS = 7 * 86400
_DURATION_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", re.IGNORECASE)


_STRUCTURAL_FULLWIDTH = "＞｜＆／：－＝；"      # 只轉換「指令結構」會用到的符號，避免動到使用者輸入的中文內容


def normalize_text(text: str) -> str:
    """把輸入法打出的全形指令符號、破折號換成半形：＞ ｜ ＆＆ ／timer １：３０ －g – —"""
    out = []
    for ch in text:
        o = ord(ch)
        if ch in _STRUCTURAL_FULLWIDTH or 0xFF10 <= o <= 0xFF19 or 0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A:
            ch = chr(o - 0xFEE0)
        elif o == 0x3000:
            ch = " "
        elif ch in "–—−‐‑":
            ch = "-"
        out.append(ch)
    return "".join(out)


def parse_duration(text: str) -> Optional[int]:
    """H:M:S、M:S、純秒數、或 1h30m10s → 秒數。無法解析或 <= 0 回傳 None。"""
    t = text.strip().lower()
    if not t:
        return None
    t = re.sub(r"小時|時|hours?|hrs?", "h", t)
    t = re.sub(r"分鐘|分|minutes?|mins?", "m", t)
    t = re.sub(r"秒鐘|秒|seconds?|secs?", "s", t)
    if re.fullmatch(r"\d+(?::\d+){0,2}", t):
        nums = [int(x) for x in t.split(":")]
        while len(nums) < 3:
            nums.insert(0, 0)
        h, m, s = nums
        total = h * 3600 + m * 60 + s
    else:
        m_ = _DURATION_RE.match(t)
        if not m_ or not any(m_.groups()):
            return None
        h, m, s = (int(x) if x else 0 for x in m_.groups())
        total = h * 3600 + m * 60 + s
    return total if 0 < total <= MAX_SECONDS else None


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def seconds_until(clock: str, now: Optional[float] = None) -> Optional[int]:
    """HH:MM[:SS] → 距離下一次該時刻還有幾秒（已過今天就算明天）。格式錯誤回傳 None。"""
    m_ = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", clock.strip())
    if not m_:
        return None
    h, mi, s = int(m_.group(1)), int(m_.group(2)), int(m_.group(3) or 0)
    if h > 23 or mi > 59 or s > 59:
        return None
    t = time.localtime(now if now is not None else time.time())
    target = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec
    want = h * 3600 + mi * 60 + s
    diff = want - target
    return diff if diff > 0 else diff + 86400


def parse_modifiers(args: list[str], *, command: str = "cool", command_key: str = "") -> tuple[list[str], Modifiers]:
    """從參數中取出 `>` 與 /修飾符，回傳 (剩下的參數, 修飾符)。

    command      顯示在錯誤訊息裡的指令名稱，例如 "cool -g"
    command_key  login / go / ... 用來檢查這個指令能不能搭配該修飾符
    """
    mods = Modifiers()

    def fail(msg: str) -> tuple[list[str], Modifiers]:
        note("WARN", msg)
        mods.ok = False
        return args, mods

    # 舊的 -s / --show 已移除
    if any(a in ("-s", "--show") for a in args):
        return fail("-s 已改為 /show，例如：cool -l /show、cool -g > /show")

    # 沒有 `>` 也沒有修飾符時原樣回傳（保留含空白的參數，例如 cool -n "我的 帳號"）
    if not any(">" in a or a.split("=", 1)[0].lower().lstrip("/") in MODIFIERS and a.startswith("/") for a in args):
        return list(args), mods

    # 切開 `>`：左邊是原本的參數，右邊只能是修飾符
    text = " ".join(args).replace(">", " > ")
    tokens = text.split()
    if ">" in tokens:
        i = tokens.index(">")
        # 第一個 `>` 之後的都是修飾符；再出現的 `>`（例如 `> /show | /timer 5`）只是分隔，忽略
        head, tail = tokens[:i], [t for t in tokens[i + 1:] if t != ">"]
        has_arrow = True
    else:
        head, tail, has_arrow = tokens, [], False

    def consume(seq: list[str], strict: bool) -> Optional[list[str]]:
        """取出 seq 裡的修飾符；strict = `>` 之後，不認得的 /xxx 要報錯。回傳剩下的參數；None = 失敗。"""
        rest: list[str] = []
        seq = _unglue(seq)
        j = 0
        while j < len(seq):
            tok = seq[j]
            name, eq, inline = tok[1:].partition("=") if tok.startswith("/") else ("", "", "")
            name = ALIASES.get(name.lower(), name.lower())
            if tok.startswith("/") and name in MODIFIERS:
                needs_value, allowed, _desc = MODIFIERS[name]
                if allowed is not None and command_key and command_key not in allowed:
                    names = " / ".join({"login": "cool -l", "go": "cool -g"}.get(k, k) for k in allowed)
                    fail(f"/{name} 只能搭配 {names}，{command} 不支援。")
                    return None
                value = ""
                if needs_value:
                    if eq:
                        value = inline
                    elif j + 1 < len(seq) and not seq[j + 1].startswith("/"):
                        j += 1
                        value = seq[j]
                    if not value or value in ("-h", "--help", "/help"):
                        hint = f"；要看說明請輸入 /{name} -h" if value else ""
                        fail(f"/{name} 後面要接值，例如：cool -g > /{name} {_example(name)}{hint}")
                        return None
                if name in mods.given and name not in ("show", "clear", "exit"):
                    fail(f"/{name} 重複了。")
                    return None
                if not _apply(mods, name, value, fail):
                    return None
                mods.given.append(name)
            elif strict and tok.startswith("/"):
                fail(f"`>` 後面不認得：{tok}（可用 {'、'.join('/' + n for n in MODIFIERS)}）")
                return None
            elif strict:
                fail(f"`>` 後面只能接 /修飾符，收到：{tok}")
                return None
            else:
                rest.append(tok)
            j += 1
        return rest

    new_head = consume(head, strict=False)
    if new_head is None:
        return args, mods
    if has_arrow:
        if not tail:
            return fail("`>` 後面要接設定，例如：/timer 1:30:00 或 /show")
        if consume(tail, strict=True) is None:
            return args, mods
    if mods.delay is not None and mods.at is not None:
        return fail("/delay 和 /at 不能同時使用。")
    return new_head, mods


_GLUED = re.compile(r"^/(timer|for|delay|at|repeat)(?=\d)(.+)$", re.IGNORECASE)


def _unglue(seq: list[str]) -> list[str]:
    """`/timer5` → `/timer`、`5`（少打空白的常見寫法）。"""
    out: list[str] = []
    for tok in seq:
        m_ = _GLUED.match(tok)
        if m_:
            out.extend(["/" + m_.group(1), m_.group(2)])
        else:
            out.append(tok)
    return out


def _example(name: str) -> str:
    return {"timer": "1:30:00", "delay": "10:00", "at": "21:30", "repeat": "3"}.get(name, "")


def _apply(mods: Modifiers, name: str, value: str, fail) -> bool:
    if name == "show":
        mods.show = True
    elif name == "clear":
        mods.clear = True
    elif name == "exit":
        mods.exit = True
    elif name == "timer":
        mods.timer = parse_duration(value)
        if mods.timer is None:
            fail(f"/timer 時間格式不正確：{value}（請用 時:分:秒，例如 1:30:00、45:00 或 90；最長 7 天）")
            return False
    elif name == "delay":
        mods.delay = parse_duration(value)
        if mods.delay is None:
            fail(f"/delay 時間格式不正確：{value}（請用 時:分:秒，例如 10:00、1:00:00 或 90）")
            return False
    elif name == "at":
        if seconds_until(value) is None:
            fail(f"/at 時刻格式不正確：{value}（請用 24 小時制 時:分，例如 21:30 或 07:05:30）")
            return False
        mods.at = value
    elif name == "repeat":
        if not value.isdigit() or not (1 <= int(value) <= 50):
            fail(f"/repeat 次數要是 1～50 的整數：{value}")
            return False
        mods.repeat = int(value)
    return True


# ── 目前正在執行的指令所帶的修飾符（由 dispatch 設定，cmd_login / cmd_go 讀取）──
_CURRENT = Modifiers()


def set_current(mods: Optional[Modifiers]) -> None:
    global _CURRENT
    _CURRENT = mods or Modifiers()


def get_current() -> Modifiers:
    return _CURRENT


__all__ = ["Modifiers", "MODIFIERS", "ALIASES", "MODIFIER_NAMES_RE", "parse_duration", "format_duration", "normalize_text",
           "seconds_until", "parse_modifiers", "set_current", "get_current"]
