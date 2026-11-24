"""依修飾符執行指令：等待（/delay、/at）、重複（/repeat）、時限（/timer）。

/timer 的做法：另開一個計時執行緒，時間到就在主執行緒丟出 CommandTimeout，
並對主控台塞一個 Enter，把卡在「等使用者輸入」的指令叫醒，讓例外立刻生效。
指令裡原本的 try/finally（關瀏覽器、還原畫面）都會照常執行。
CommandTimeout 繼承 BaseException，所以指令內的 `except Exception` 不會誤吞它。
"""
from __future__ import annotations
import ctypes
import os
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from typing import Callable

from ._compat import *
from .colors import *
from .modifiers import Modifiers, format_duration, seconds_until


EXIT = object()          # 要求離開 cool>（/exit 修飾符、/exit 指令共用）


class CommandTimeout(BaseException):
    """指令超過 /timer 設定的時間。"""


# ───────────── 主控台輸入：叫醒 / 清空 ─────────────
def _console_input_handle():
    if sys.platform != "win32":
        return None
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = ctypes.c_void_p
    h = k32.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)   # GENERIC_READ|WRITE, SHARE_READ|WRITE, OPEN_EXISTING
    if h in (None, ctypes.c_void_p(-1).value, 0xFFFFFFFFFFFFFFFF, -1):
        return None
    return h


class _KEY_EVENT(ctypes.Structure):
    _fields_ = [("bKeyDown", ctypes.c_int), ("wRepeatCount", ctypes.c_ushort),
                ("wVirtualKeyCode", ctypes.c_ushort), ("wVirtualScanCode", ctypes.c_ushort),
                ("uChar", ctypes.c_wchar), ("dwControlKeyState", ctypes.c_uint)]


class _INPUT_RECORD(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("KeyEvent", _KEY_EVENT)]
    _anonymous_ = ("u",)
    _fields_ = [("EventType", ctypes.c_ushort), ("u", _U)]


def _wake_console_reader() -> None:
    """塞一個 Enter 到主控台輸入，讓卡在 input()/getwch() 的主執行緒醒來。"""
    if sys.platform != "win32" or not (sys.stdin and sys.stdin.isatty()):
        return
    try:
        h = _console_input_handle()
        if h is None:
            return
        recs = (_INPUT_RECORD * 2)()
        for i, down in enumerate((1, 0)):
            recs[i].EventType = 1                      # KEY_EVENT
            recs[i].KeyEvent = _KEY_EVENT(down, 1, 0x0D, 0x1C, "\r", 0)
        written = ctypes.c_uint(0)
        ctypes.windll.kernel32.WriteConsoleInputW(ctypes.c_void_p(h), recs, 2, ctypes.byref(written))
        ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(h))
    except Exception:
        pass


def _flush_console_input() -> None:
    if sys.platform != "win32" or not (sys.stdin and sys.stdin.isatty()):
        return
    try:
        h = _console_input_handle()
        if h is not None:
            ctypes.windll.kernel32.FlushConsoleInputBuffer(ctypes.c_void_p(h))
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(h))
    except Exception:
        pass


# ───────────── /timer：時限 ─────────────
@contextmanager
def time_limit(seconds: int):
    """在 with 區塊內執行的指令超過 seconds 秒就丟出 CommandTimeout。"""
    main_id = threading.get_ident()
    done = threading.Event()
    fired = threading.Event()

    def watch():
        if done.wait(seconds):
            return
        fired.set()
        if sys.platform == "win32":
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(main_id), ctypes.py_object(CommandTimeout))
            _wake_console_reader()
        else:                                           # pragma: no cover
            import _thread
            _thread.interrupt_main()
        # 管線輸入（桌面應用程式）沒辦法叫醒讀取中的指令：整個程序只為這一個指令而存在，直接結束
        if not done.wait(4):
            sys.stdout.write("\n")
            note("WARN", f"指令超過時限 {format_duration(seconds)} 且無法中斷，結束程序。")
            sys.stdout.flush()
            os._exit(124)

    t = threading.Thread(target=watch, daemon=True, name="cool-timer")
    t.start()
    try:
        yield
    finally:
        done.set()
        if fired.is_set():
            # 例外可能還沒被投遞：清掉，免得之後在不相干的地方冒出來；並清掉多塞的 Enter
            if sys.platform == "win32":
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(main_id), None)
            _flush_console_input()


# ───────────── /delay、/at：等待 ─────────────
def wait_before(seconds: int, label: str, prefix: str = "  ", count_label: str = "距離開始") -> bool:
    """倒數等待；Ctrl+C 取消。回傳 False 表示被取消。"""
    tty = bool(sys.stdin) and sys.stdin.isatty()
    print(f"{prefix}{label}，等待 {format_duration(seconds)}（Ctrl+C 取消）")
    deadline = time.monotonic() + seconds
    last = -1
    try:
        while True:
            remaining = int(deadline - time.monotonic() + 0.999)
            if remaining <= 0:
                break
            if remaining != last:
                last = remaining
                if tty:
                    sys.stdout.write(f"\r  {count_label} {format_duration(remaining)}   ")
                    sys.stdout.flush()
                elif remaining % 60 == 0 or remaining <= 5:
                    print(f"  {count_label} {format_duration(remaining)}", flush=True)
            time.sleep(0.25)
    except KeyboardInterrupt:
        print()
        note("INFO", "已取消。")
        return False
    if tty:
        sys.stdout.write("\r" + " " * 30 + "\r")
    return True


# ───────────── 總入口 ─────────────
def clear_screen() -> None:
    try:
        subprocess.run(["clear" if os.name != "nt" else "cls"], shell=(os.name == "nt"))
    except Exception:
        os.system("clear" if os.name != "nt" else "cls")


def run_with_modifiers(mods: Modifiers, func: Callable[[], object], *, own_timer: bool = False, hold: bool = False):
    """依修飾符執行 func（回傳 True/False 表示成功與否；其他值如離開訊號會原樣回傳）。

    own_timer  指令自己處理 /timer（例如 cool -g 是「瀏覽器開啟多久」），這裡就不再套全域時限。
    逾時視為「依設定正常結束」，回傳 True，所以 `cool -c > /timer 5 && /clear` 會接著清畫面。
    hold        指令只是輸出資料（-h、-v、-t…）時，/timer 要讓時間走完（顯示倒數），而不是立刻返回。
    /clear      全部做完後清除畫面；有 /timer 而指令提早結束（例如 cool -h）時，畫面保留到時間到才清，
                也就是「顯示 5 秒再清掉」。保留期間 Ctrl+C 取消（不清）。
    """
    if mods.delay is not None or mods.at is not None:
        if mods.at is not None:
            secs = seconds_until(mods.at) or 0
            label = f"排定 {mods.at} 開始"
        else:
            secs = mods.delay or 0
            label = "延後開始"
        if not wait_before(secs, label):
            return False

    ok: object = True
    started = time.monotonic()
    for run in range(1, mods.repeat + 1):
        if mods.repeat > 1:
            note("INFO", f"第 {run}/{mods.repeat} 次")
        try:
            if mods.timer and not own_timer:
                with time_limit(mods.timer):
                    result = func()
            else:
                result = func()
            ok = result if (result is not True and result is not False and result is not None) else bool(result)
        except CommandTimeout:
            print()
            note("WARN", f"指令超過 /timer {format_duration(mods.timer or 0)}，已自動中止。")
            ok = True
        except KeyboardInterrupt:
            print()
            note("INFO", "已中斷。")
            return False
        if ok is not True:
            break

    if isinstance(ok, bool) and mods.timer and not own_timer and (hold or mods.clear):
        # 指令比時限早做完：把剩下的時間走完，讓 /timer 看得到、後面的 && / /clear 也會等到時間到才接著做
        left = int(mods.timer - (time.monotonic() - started) + 0.999)
        if left > 0:
            label = "畫面保留中，之後清除" if mods.clear else "計時中"
            if not wait_before(left, label, count_label="剩餘"):
                return ok
        if not mods.clear:
            note("INFO", f"計時結束（{format_duration(mods.timer)}）。")
    if mods.clear and isinstance(ok, bool):
        clear_screen()
    if mods.exit and isinstance(ok, bool):
        note("INFO", "再見。")
        return EXIT
    return ok


__all__ = ["EXIT", "CommandTimeout", "time_limit", "wait_before", "run_with_modifiers", "clear_screen"]
