"""互動式 cool> 的單行輸入。

Windows 主控台內建的 input()（cooked read）會記住「提示符號開始的位置」。
終端機視窗縮放、重新折行之後，這個位置就過期了，之後輸入的字會印在舊的那一列、
蓋掉前面的輸出（內嵌終端機拖曳縮放時最明顯）。

這裡改成自己逐鍵讀取、只用「相對游標」輸出，所以縮放後仍然跟著目前游標位置。
功能：左右/Home/End/Delete/Backspace、上下鍵歷史、Ctrl+U/Ctrl+K、Ctrl+C、Ctrl+D。
非 Windows 或 stdin 不是終端機時，直接退回內建 input()。
"""
from __future__ import annotations
import sys
import unicodedata

_history: list[str] = []


def _w(ch: str) -> int:
    """終端機顯示寬度（全形 2、組合字 0）。"""
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _width(s: str) -> int:
    return sum(_w(c) for c in s)


def _visible_len(prompt: str) -> int:
    import re
    return _width(re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", prompt))


def read_line(prompt: str) -> str:
    if sys.platform != "win32" or not (sys.stdin and sys.stdin.isatty()):
        return input(prompt)
    try:
        import msvcrt
    except ImportError:                      # pragma: no cover
        return input(prompt)

    out = sys.stdout
    out.write(prompt)
    out.flush()

    buf: list[str] = []
    pos = 0                                  # 游標在 buf 中的位置
    hist_i = len(_history)
    saved = ""                               # 瀏覽歷史前正在輸入的內容

    def left(n: int):
        if n > 0:
            out.write(f"\x1b[{n}D")

    def right(n: int):
        if n > 0:
            out.write(f"\x1b[{n}C")

    def redraw_tail(old_tail_w: int = 0):
        """從游標處重寫尾端，清掉多出來的舊字，再把游標放回 pos。"""
        tail = "".join(buf[pos:])
        out.write(tail)
        extra = old_tail_w - _width(tail)
        if extra > 0:
            out.write(" " * extra)
            left(extra)
        left(_width(tail))

    def replace_all(text: str):
        nonlocal pos
        left(_width("".join(buf[:pos])))
        old_w = _width("".join(buf))
        buf[:] = list(text)
        pos = len(buf)
        out.write(text)
        extra = old_w - _width(text)
        if extra > 0:
            out.write(" " * extra)
            left(extra)

    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            out.write("\r\n")
            out.flush()
            line = "".join(buf)
            if line.strip() and (not _history or _history[-1] != line):
                _history.append(line)
            return line
        if ch == "\x03":
            out.write("\r\n")
            out.flush()
            raise KeyboardInterrupt
        if ch == "\x04" or ch == "\x1a":
            if not buf:
                out.write("\r\n")
                out.flush()
                raise EOFError
            continue
        if ch in ("\x00", "\xe0"):
            k = msvcrt.getwch()
            if k == "K" and pos > 0:                     # ←
                pos -= 1
                left(_w(buf[pos]))
            elif k == "M" and pos < len(buf):            # →
                right(_w(buf[pos]))
                pos += 1
            elif k == "G":                               # Home
                left(_width("".join(buf[:pos])))
                pos = 0
            elif k == "O":                               # End
                right(_width("".join(buf[pos:])))
                pos = len(buf)
            elif k == "S" and pos < len(buf):            # Delete
                old = _width("".join(buf[pos:]))
                del buf[pos]
                redraw_tail(old)
            elif k == "H" and hist_i > 0:                # ↑
                if hist_i == len(_history):
                    saved = "".join(buf)
                hist_i -= 1
                replace_all(_history[hist_i])
            elif k == "P" and hist_i < len(_history):    # ↓
                hist_i += 1
                replace_all(saved if hist_i == len(_history) else _history[hist_i])
            out.flush()
            continue
        if ch in ("\x08", "\x7f"):                       # Backspace
            if pos > 0:
                pos -= 1
                w = _w(buf[pos])
                old = _width("".join(buf[pos:]))
                del buf[pos]
                left(w)
                redraw_tail(old)
        elif ch == "\x15":                               # Ctrl+U：刪到行首
            prefix_w = _width("".join(buf[:pos]))
            left(prefix_w)
            del buf[:pos]
            pos = 0
            tail = "".join(buf)
            out.write(tail + " " * prefix_w)
            left(prefix_w + _width(tail))
        elif ch == "\x0b":                               # Ctrl+K：刪到行尾
            old = _width("".join(buf[pos:]))
            del buf[pos:]
            out.write(" " * old)
            left(old)
        elif ch == "\x1b":                               # Esc：清空整行
            replace_all("")
        elif ch >= " ":
            buf.insert(pos, ch)
            pos += 1
            if pos == len(buf):
                out.write(ch)
            else:
                out.write(ch)
                redraw_tail()
        out.flush()
