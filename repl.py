"""Interactive cool> command loop."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *
from .security import *
from .accounts import *
from .terminal_input import *
from .colorpicker import *
from .help import *
from .version import *
from .commands.account import *
from .commands.time_report import *
from .commands.urls import *

PROMPT = f"{CYAN}cool>{RESET} "
HISTORY_FILE = _BASE / ".cool_history"

def repl(mgr: AccountManager):
    if readline:
        try:
            if HISTORY_FILE.exists():
                readline.read_history_file(str(HISTORY_FILE))
            readline.set_history_length(1000)
        except Exception:
            pass

    while True:
        try:
            line = _strip_control_sequences(input(PROMPT))
            if readline and line:
                try:
                    readline.write_history_file(str(HISTORY_FILE))
                except Exception:
                    pass
        except (EOFError, KeyboardInterrupt):
            print()
            note("INFO", "再見。")
            break
        if not line:
            continue
        reset_sudo()

        if line.lower() == "sudo" or line.lower().startswith("sudo "):
            parts_s = line.split()
            s_args = parts_s[1:]
            if any(a in ("-h","--help","/help") for a in s_args):
                print(CMD_HELP["sudo"])
                continue
            try:
                _, rest_sudo = line.split(None, 1)
                rest_sudo = rest_sudo.strip()
            except ValueError:
                rest_sudo = ""
            if not rest_sudo:
                if has_sudo():
                    note("INFO", "已取得 cool sudo 權限")
                continue
            if rest_sudo.lower().startswith("cool ") or rest_sudo.startswith("/"):
                if not has_sudo():
                    continue
                line = rest_sudo
            else:
                note("WARN", f"未知 sudo 用法：{line}（可用 sudo / sudo cool -s / /passwd）")
                continue

        if line.startswith("/"):
            parts = line[1:].split()
            if not parts:
                continue
            raw = "/" + parts[0]
            args = parts[1:]
            cmd = parts[0]
            if not args and raw == "/IG":
                print("製作者IG：c.pls._")
                print("https://www.instagram.com/c.pls._/")
                continue
            if not args and raw == "/INEEDLINK":
                print("連結收藏：")
                print("https://docs.google.com/document/d/14c3QKaOBrai301l9r5-XlVf2EXsO9io-mFBwQ-K7djo/edit?usp=sharing")
                continue
            if cmd in ("exit", "quit", "q"):
                if any(a in ("-h","--help","/help") for a in args):
                    print(CMD_HELP["exit"])
                    continue
                note("INFO", "再見。")
                break
            elif cmd in ("clear", "cls", "c"):
                if any(a in ("-h","--help","/help") for a in args):
                    print(CMD_HELP["clear"])
                    continue
                try:
                    subprocess.run(["clear" if os.name != "nt" else "cls"], shell=False)
                except Exception:
                    os.system("clear" if os.name != "nt" else "cls")
            elif cmd in ("passwd", "pwd"):
                if any(a in ("-h","--help","/help") for a in args):
                    print(CMD_HELP["passwd"])
                    continue
                cmd_passwd(mgr, args)
            elif cmd in ("help", "h"):
                print(HELP_TEXT)
            else:
                note("WARN", f"未知 slash 指令：{raw}（可用 /clear /passwd /exit /help）")
            continue

        if not line.lower().startswith("cool "):
            note("WARN", f"未知指令：{line}（dash 參數需以 cool 開頭，例如 cool -h；slash 指令用 /clear /passwd /exit）")
            continue

        try:
            _, rest = line.split(None, 1)
            rest = rest.strip()
        except ValueError:
            rest = ""
        if rest.lower().startswith("cool"):
            try:
                _, rest = rest.split(None, 1)
                rest = rest.strip()
            except ValueError:
                rest = ""
        if not rest:
            note("WARN", "請輸入參數，例如 cool -h / cool --help / cool -s")
            continue
        if rest in ("-v", "--version"):
            print(VERSION)
            continue
        if rest.lower().startswith("sudo"):
            parts = rest.split()
            s_args = parts[1:]
            if any(a in ("-h","--help","/help") for a in s_args):
                print(CMD_HELP["sudo"])
                continue
            if not s_args:
                if has_sudo():
                    note("INFO", "已取得 cool sudo 權限")
                continue
            if s_args[0].lower() == "cool":
                rest = " ".join(s_args[1:])
                if not rest:
                    continue
                if not rest.startswith("-"):
                    note("WARN", f"未知指令：cool sudo {rest}（輸入 cool -h 查看）")
                    continue
                parts = rest.split()
                raw = parts[0]
                args = parts[1:]
                cmd = raw.lstrip("-")
                if any(a in ("-h","--help","/help") for a in args):
                    key = {"l":"login","login":"login","a":"account","account":"account","acc":"account","s":"show","show":"show","n":"name","name":"name","t":"time","time":"time","u":"url","url":"url","visit":"url","w":"write","write":"write","workspace":"workspace","split":"workspace","d":"delete","delete":"delete","color":"color","colour":"color","h":"help","help":"help"}.get(cmd, "")
                    if raw.lower() in ("--color","--colour"):
                        key = "color"
                    if raw == "-c":
                        key = "color"
                    if key in CMD_HELP:
                        print(CMD_HELP[key])
                    else:
                        print(HELP_TEXT)
                    continue
                if raw.lower() in ("--color","--colour") or cmd.lower() in ("color","colour"):
                    cmd_color(mgr, args)
                elif raw == "-c":
                    cmd_color(mgr, args)
                elif raw == "-H":
                    print("  /IG                         顯示製作者 IG 名稱與主頁面")
                    print("  /INEEDLINK                  顯示所有課程連結")
                elif raw in ("-h", "--help"):
                    print(HELP_TEXT)
                elif raw in ("-l", "--login"):
                    if not has_sudo():
                        continue
                    cmd_login(mgr, args)
                elif raw in ("-a", "--account", "--acc"):
                    cmd_account(mgr, args)
                elif raw in ("-A", "--ALL"):
                    cmd_show(mgr)
                elif raw in ("-n", "--name", "--rename"):
                    cmd_name(mgr, args)
                elif raw in ("-t", "--time"):
                    cmd_time(mgr, args)
                elif raw in ("-u", "--url", "--visit"):
                    cmd_url(mgr, args)
                elif raw in ("-d", "--delete", "--remove", "--rm"):
                    cmd_delete(mgr, args)
                else:
                    note("WARN", f"未知指令：cool sudo {raw}（輸入 cool -h 查看）")
                continue
            note("WARN", f"未知 sudo 用法：cool sudo {' '.join(s_args)}")
            continue

        if not rest.startswith("-"):
            note("WARN", f"參數需以 - 開頭，例如 cool -h，收到：{rest}")
            continue

        parts = rest.split()
        raw = parts[0]
        args = parts[1:]
        cmd = raw.lstrip("-")

        if any(a in ("-h","--help","/help") for a in args):
            key = {"l":"login","login":"login","a":"account","account":"account","acc":"account","s":"show","show":"show","n":"name","name":"name","t":"time","time":"time","u":"url","url":"url","visit":"url","d":"delete","delete":"delete","w":"workspace","workspace":"workspace","split":"workspace","color":"color","colour":"color","colors":"color","h":"help","help":"help"}.get(cmd, "")
            if raw.lower() in ("--color","--colour","--colors") or raw == "-c":
                key = "color"
            if key in CMD_HELP:
                print(CMD_HELP[key])
            else:
                print(HELP_TEXT)
            continue

        if raw.lower() in ("--color","--colour","--colors") or cmd.lower() in ("color","colour","colors"):
            cmd_color(mgr, args)
        elif raw == "-c":
            if args and args[0].lower() in ("--color","--colour","--colors"):
                cmd_color(mgr, args[1:])
            else:
                cmd_color(mgr, args)
        elif raw == "-H":
            print("  /IG                         顯示製作者 IG 名稱與主頁面")
            print("  /INEEDLINK                  顯示所有課程連結")
        elif raw in ("-h", "--help"):
            print(HELP_TEXT)
        elif raw in ("-l", "--login"):
            cmd_login(mgr, args)
        elif raw in ("-a", "--account", "--acc"):
            cmd_account(mgr, args)
        elif raw in ("-A", "--ALL"):
            cmd_show(mgr)
        elif raw in ("-n", "--name", "--rename"):
            cmd_name(mgr, args)
        elif raw in ("-t", "--time"):
            cmd_time(mgr, args)
        elif raw in ("-u", "--url", "--visit"):
            cmd_url(mgr, args)
        elif raw in ("-d", "--delete", "--remove", "--rm"):
            cmd_delete(mgr, args)
        elif raw in ("passwd", "--passwd"):
            cmd_passwd(mgr, args)
        else:
            note("WARN", f"未知指令：cool {raw}（輸入 cool -h 查看）")

__all__ = [name for name in globals() if not name.startswith("__")]
