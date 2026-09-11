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

OPTIONAL_STDLIB_MODULES = set()
PACKAGE_DESCRIPTIONS = {
    "playwright": "登入、瀏覽課程網址及取得學習時間需要它；缺少時這些功能無法使用。",
}
DEBUG_MODE = (
    os.environ.get("COOL_DEBUG", "").lower() in ("1", "true", "yes", "on")
    or "--debug" in sys.argv[1:]
    or "-D" in sys.argv[1:]
)
if DEBUG_MODE:
    sys.argv = [sys.argv[0], *(
        arg for arg in sys.argv[1:] if arg not in ("--debug", "-D")
    )]


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
    local_modules = {
        source_file.stem for source_file in PROJECT_DIR.glob("*.py")
    } | {"commands", "cool_app"}
    for display_name, import_name in sorted(modules):
        top_level = import_name.split(".", 1)[0]
        if os.name == "nt" and top_level == "curses":
            continue
        if top_level in local_modules:
            kind = "本地模組"
        elif top_level in stdlib:
            kind = "標準庫"
        elif top_level == "cool_app":
            kind = "本地模組"
        else:
            kind = "第三方套件"
        discovered.append((display_name, import_name, kind))
    return discovered

def _debug(message: str):
    if DEBUG_MODE:
        note("DEBUG", message)

def _describe_missing(module: str) -> str:
    package = module.split(".", 1)[0]
    return PACKAGE_DESCRIPTIONS.get(
        package,
        f"需要使用 {module} 相關功能；缺少時使用該功能會失敗。",
    )

def _module_available(module: str, kind: str) -> tuple[bool, str]:
    """Check both module discovery and actual import, especially curses on Windows."""
    try:
        if importlib.util.find_spec(module) is None:
            return False, f"找不到模組 {module}"
        if kind == "第三方套件" or module == "curses":
            __import__(module)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

def _ask_install(package: str, install_all: bool) -> tuple[bool, bool]:
    """Ask whether to install one package; return (install, install_all)."""
    if install_all:
        return True, True
    prompt = (
        f"\n找不到套件「{package}」。是否現在安裝？"
        " [y/n/a] (yes/no/all): "
    )
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = "n"
    if answer in ("a", "all"):
        return True, True
    if answer in ("y", "yes"):
        return True, False
    return False, False

def _install_packages(packages: list[str]) -> list[str]:
    """Interactively install missing packages and return packages declined/failed."""
    declined = []
    install_all = False
    for module_name in packages:
        package = module_name
        should_install, install_all = _ask_install(package, install_all)
        if not should_install:
            declined.append(package)
            note("WARN", f"未安裝 {package}：{_describe_missing(package)}")
            continue

        status_line(f"安裝 Python 套件 {package}", "WORK")
        command = [sys.executable, "-m", "pip", "install", package]
        result = subprocess.run(command, capture_output=True, text=True)
        if (
            result.returncode != 0
            and os.name == "nt"
            and any(word in (result.stderr or "").lower() for word in ("access is denied", "permission", "拒絕"))
        ):
            _debug(f"{package} 一般安裝被拒絕，改用目前使用者安裝")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", package],
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            status_line(f"安裝 Python 套件 {package}", "FAILED")
            declined.append(package)
            detail = (result.stderr or result.stdout or "pip 沒有提供錯誤訊息").strip()
            note("ERR", f"{package} 安裝失敗：{detail}")
            _debug(f"pip command: {' '.join(command)}")
            continue
        status_line(f"安裝 Python 套件 {package}", "DONE")

    return declined

def ensure_python_dependencies():
    """Check imports, explain failures, and ask before installing packages."""
    dependencies = _discovered_imports()
    missing_third_party = []
    missing_required = []
    for display_name, import_name, kind in dependencies:
        available, reason = _module_available(import_name, kind)
        if not available:
            _debug(f"檢查 {display_name} 失敗：{reason}")
        shown_name = display_name
        if available:
            status_line(f"{kind} {shown_name}", "OK")
        elif import_name in OPTIONAL_STDLIB_MODULES:
            status_line(f"{kind} {shown_name}", "SKIP")
        elif kind == "第三方套件":
            package = import_name.split(".", 1)[0]
            status_line(f"{kind} {package}", "DEPEND")
            missing_third_party.append(import_name.split(".", 1)[0])
        else:
            status_line(f"{kind} {display_name}", "FAILED")
            missing_required.append(display_name)
            _debug(f"必要模組不存在：{display_name} ({import_name})")

    missing_third_party = sorted(set(missing_third_party))
    if missing_required:
        note("ERR", f"缺少必要模組：{', '.join(missing_required)}")
        note("INFO", "這些模組屬於 Python 或本地程式的一部分，無法透過 pip 安全補救。")
        sys.exit(1)
    if not missing_third_party:
        return

    failed = _install_packages(missing_third_party)
    if failed:
        note("ERR", f"未完成的套件：{', '.join(failed)}")
        note("INFO", "程式將停止，因為缺少套件會導致登入、瀏覽器或互動功能無法正常運作。")
        sys.exit(1)

    for module_name in missing_third_party:
        package = module_name
        available, reason = _module_available(module_name, "第三方套件")
        if not available:
            status_line(f"重新檢查套件 {package}", "FAILED")
            note("ERR", f"{package} 安裝後仍無法載入：{reason}")
            sys.exit(1)
        status_line(f"重新檢查套件 {package}", "OK")

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
                install_dir / "chrome-win" / "chrome.exe",
                install_dir / "chrome-win64" / "chrome.exe",
                install_dir / "chrome-linux64" / "chrome",
                install_dir / "chrome-linux" / "chrome",
                install_dir / "chrome",
            )
            if any(path.is_file() and os.access(path, os.X_OK) for path in candidates):
                status_line("檢查 Chromium 瀏覽器", "OK")
                return

    note("WARN", "找不到 Playwright Chromium。")
    note("INFO", "不安裝時，登入、網址瀏覽及學習時間功能會無法啟動瀏覽器。")
    should_install, _ = _ask_install("Playwright Chromium", False)
    if not should_install:
        sys.exit(1)

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
    if DEBUG_MODE:
        _debug(f"Python：{sys.version.split()[0]}")
        _debug(f"執行檔：{sys.executable}")
        _debug(f"作業系統：{sys.platform} ({os.name})")
        _debug(f"工作目錄：{Path.cwd()}")
        _debug(f"專案目錄：{PROJECT_DIR}")
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
