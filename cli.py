"""CLI environment checks and process entry point."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *
from .security import *
from .accounts import *
from .colorpicker import *
from .help import *
from .version import *
from .repl import *
from .commands.account import *
from .commands.time_report import *
from .commands.urls import *
import ast


def _discovered_imports() -> list[tuple[str, str, str]]:
    """Discover every imported module and classify it without a dependency list."""
    modules: set[tuple[str, str]] = set()
    source_files = [
        *PROJECT_DIR.glob("*.py"),
        *PROJECT_DIR.glob("commands/**/*.py"),
        *PROJECT_DIR.glob("cool_app/**/*.py"),
    ]
    stdlib = getattr(sys, "stdlib_module_names", set())
    for source_file in source_files:
        if not source_file.is_file():
            continue
        try:
            tree = ast.parse(source_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add((alias.name, alias.name.split(".", 1)[0]))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    relative_parts = source_file.relative_to(PROJECT_DIR).with_suffix("").parts
                    package_parts = relative_parts[:-1]
                    if node.level > 1:
                        package_parts = package_parts[:-(node.level - 1)]
                    module_parts = package_parts + tuple((node.module or "").split("."))
                    display_name = ".".join(module_parts)
                    modules.add((display_name, display_name.split(".", 1)[0]))
                elif node.module and node.module != "__future__":
                    modules.add((node.module, node.module.split(".", 1)[0]))

    discovered = []
    for display_name, import_name in sorted(modules):
        top_level = import_name.split(".", 1)[0]
        if top_level in stdlib:
            kind = "標準庫"
        elif top_level == "cool_app":
            kind = "本地模組"
        else:
            kind = "第三方套件"
        discovered.append((display_name, import_name, kind))
    return discovered

def ensure_python_dependencies():
    """Show and check every discovered import, installing missing third parties."""
    dependencies = _discovered_imports()
    missing_third_party = []
    missing_required = []
    for display_name, import_name, kind in dependencies:
        available = importlib.util.find_spec(import_name) is not None
        if available:
            status_line(f"{kind} {display_name}", "OK")
        elif kind == "第三方套件":
            status_line(f"{kind} {display_name}", "DEPEND")
            missing_third_party.append(import_name.split(".", 1)[0])
        else:
            status_line(f"{kind} {display_name}", "FAILED")
            missing_required.append(display_name)

    missing_third_party = sorted(set(missing_third_party))
    if missing_required:
        note("ERR", f"缺少必要模組：{', '.join(missing_required)}")
        sys.exit(1)
    if not missing_third_party:
        return

    status_line("安裝缺少的 Python 套件", "WORK")
    result = None
    for extra in (["--break-system-packages"], []):
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", *missing_third_party, *extra],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            break
        if "no such option" not in result.stderr.lower() and "unrecognized" not in result.stderr.lower():
            break

    if result is None or result.returncode != 0:
        status_line("安裝缺少的 Python 套件", "FAILED")
        note("ERR", f"無法安裝：{', '.join(missing_third_party)}")
        print(result.stderr if result else "")
        sys.exit(1)

    for module in missing_third_party:
        if importlib.util.find_spec(module) is None:
            status_line(f"第三方套件 {module}", "FAILED")
            note("ERR", f"套件安裝後仍無法載入：{module}")
            sys.exit(1)
        status_line(f"第三方套件 {module}", "OK")

def ensure_chromium_installed():
    probe = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
        capture_output=True, text=True,
    )
    if probe.returncode == 0:
        match = re.search(
            r"Chrome for Testing .*?\n\s+Install location:\s+(.+)",
            probe.stdout,
        )
        if match:
            install_dir = Path(match.group(1).strip())
            candidates = (
                install_dir / "chrome-linux64" / "chrome",
                install_dir / "chrome-linux" / "chrome",
                install_dir / "chrome",
            )
            if any(path.is_file() and os.access(path, os.X_OK) for path in candidates):
                status_line("檢查 Chromium 瀏覽器", "OK")
                return

    status_line("下載 Chromium 瀏覽器", "WORK")
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        status_line("下載 Chromium 瀏覽器", "FAILED")
        note("ERR", "請手動執行： playwright install chromium")
        print(result.stderr)
        sys.exit(1)
    status_line("下載 Chromium 瀏覽器", "DONE")

def main():
    if any(a in ("-v", "--version") for a in sys.argv[1:]):
        print(VERSION)
        sys.exit(0)

    if any(a in ("-h", "--help", "/help") for a in sys.argv[1:]):
        cmd = None
        for a in sys.argv[1:]:
            if a in ("-h","--help","/help"):
                continue
            c = a.lstrip("-/").lower()
            if c in ("l","login"): cmd = "login"; break
            if c in ("s","show","list","ls"): cmd = "show"; break
            if c in ("n","name","rename"): cmd = "name"; break
            if c in ("t","time"): cmd = "time"; break
            if c in ("d","delete","remove","rm"): cmd = "delete"; break
            if c in ("color","colour","colors") or c == "c": cmd = "color"; break
            if c == "passwd": cmd = "passwd"; break
            if c == "sudo": cmd = "sudo"; break
        if cmd and cmd in CMD_HELP:
            print(CMD_HELP[cmd])
        else:
            print(HELP_TEXT)
        sys.exit(0)

    if len(sys.argv) == 2 and sys.argv[1] in ("/exit", "/quit", "-e", "--exit"):
        sys.exit(0)

    # Color configuration is local and does not need the browser environment.
    if len(sys.argv) > 1:
        raw1 = sys.argv[1]
        if raw1 == "-c" or raw1.lower() in ("--color", "--colour", "--colors"):
            args = sys.argv[2:]
            if raw1 == "-c" and args and args[0].lower() in ("--color", "--colour", "--colors"):
                args = args[1:]
            cmd_color(None, args)
            sys.exit(0)

    status_line("環境檢查", "WORK")
    ensure_python_dependencies()
    ensure_chromium_installed()
    status_line("環境檢查", "OK")
    print()

    mgr = AccountManager()

    if len(sys.argv) > 1:
        raw1 = sys.argv[1]
        cmd = raw1.lstrip("-/").lower()
        args = sys.argv[2:]
        if raw1 == "-H":
            print("  /IG                         顯示製作者 IG 名稱與主頁面")
            print("  /INEEDLINK                  顯示所有課程連結")
        elif raw1 in ("-l", "--login"):
            cmd_login(mgr, args)
        elif raw1 in ("-a", "--account", "--acc"):
            cmd_account(mgr, args)
        elif raw1 in ("-A", "--ALL"):
            cmd_show(mgr)
        elif raw1 in ("-n", "--name", "--rename"):
            cmd_name(mgr, args)
        elif raw1 in ("-t", "--time"):
            cmd_time(mgr, args)
        elif raw1 in ("-u", "--url", "--visit"):
            cmd_url(mgr, args)
        elif raw1 in ("-d", "--delete", "--remove", "--rm"):
            cmd_delete(mgr, args)
        elif raw1 in ("passwd", "--passwd"):
            cmd_passwd(mgr, args)
        else:
            note("WARN", f"未知參數：{sys.argv[1]}")
            print(HELP_TEXT)
            sys.exit(1)
        sys.exit(0)

    repl(mgr)

__all__ = [name for name in globals() if not name.startswith("__")]
