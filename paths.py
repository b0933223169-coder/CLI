"""Project and persistent-data paths."""
from __future__ import annotations
from ._compat import *
import platform as _platform

BASE_URL = "https://www.coolenglish.edu.tw"
LOGIN_URL = f"{BASE_URL}/login/index.php"
DEFAULT_TARGET = f"{BASE_URL}/time/time_view_detail_by_people.php?id=2055519"

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = (
    PACKAGE_DIR.parent
    if (PACKAGE_DIR / "cool_app").is_dir() and not (PACKAGE_DIR / "cli.py").is_file()
    else PACKAGE_DIR
)

def _base_dir() -> Path:
    try:
        base = PROJECT_DIR
        test = base / ".cool_write_test"
        try:
            test.touch(exist_ok=True)
            test.unlink(missing_ok=True)
            return base
        except Exception:
            pass
    except Exception:
        pass
    fallback = Path.home() / ".config" / "cool"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

_BASE = _base_dir()
COOKIE_DIR = _BASE / "cookies"
ACCOUNTS_FILE = _BASE / "accounts.json"
LEGACY_COOKIE = PROJECT_DIR / "cookies.txt"
COLORS_FILE = _BASE / "colors.json"
PASSWD_FILE = _BASE / ".cool_passwd"
URLS_FILE = _BASE / "urls.txt"

for _old, _new in [
    (PROJECT_DIR / "accounts.json", ACCOUNTS_FILE),
    (PROJECT_DIR / "colors.json", COLORS_FILE),
    (PROJECT_DIR / ".cool_passwd", PASSWD_FILE),
]:
    try:
        if _old.exists() and not _new.exists():
            _new.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_old, _new)
            try:
                _new.chmod(0o600)
            except Exception:
                pass
    except Exception:
        pass

def _atomic_write(path: Path, data: str, mode: int = 0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".tmp.")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(data)
        Path(tmp).chmod(mode)
        Path(tmp).replace(path)
        try:
            path.chmod(mode)
        except Exception:
            pass
    finally:
        try:
            if Path(tmp).exists():
                Path(tmp).unlink()
        except Exception:
            pass

def _sanitize_filename(name: str, max_len: int = 80) -> str:
    name = name.strip()
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    safe = re.sub(r"_+", "_", safe).strip("._-") or "default"
    if len(safe) > max_len:
        safe = safe[: max_len - 9] + "_" + h
    if safe in ("", ".", ".."):
        safe = f"default_{h}"
    if safe.startswith("-"):
        safe = "_" + safe
    return safe

# ── 啟動時從本機自動抓真實 fingerprint ────────────────────────────────────────

def _get_real_fingerprint() -> dict:
    """啟動時讀本機真實值，讓 Playwright 偽裝成這台電腦。"""

    # 螢幕解析度
    width, height = 1920, 1080
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            width  = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
        except Exception:
            pass

    # CPU 核心數
    cpu_count = os.cpu_count() or 4

    # 記憶體（取最近 2 的次方：4/8/16/32）
    mem_gb = 8
    if os.name == "nt":
        try:
            import ctypes
            class _MEMSTAT(ctypes.Structure):
                _fields_ = [
                    ("dwLength",                ctypes.c_ulong),
                    ("dwMemoryLoad",            ctypes.c_ulong),
                    ("ullTotalPhys",            ctypes.c_ulonglong),
                    ("ullAvailPhys",            ctypes.c_ulonglong),
                    ("ullTotalPageFile",        ctypes.c_ulonglong),
                    ("ullAvailPageFile",        ctypes.c_ulonglong),
                    ("ullTotalVirtual",         ctypes.c_ulonglong),
                    ("ullAvailVirtual",         ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = _MEMSTAT()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            raw_gb = stat.ullTotalPhys / (1024 ** 3)
            for candidate in [4, 8, 16, 32]:
                if raw_gb <= candidate:
                    mem_gb = candidate
                    break
        except Exception:
            pass

    # Windows 版本 → sec-ch-ua-platform-version
    # Win11 build ≥ 22000 → "15.0.0"，Win10 → "10.0.0"
    platform_version = "10.0.0"
    try:
        ver = _platform.version()       # e.g. "10.0.22631"
        build = int(ver.split(".")[2]) if ver.count(".") >= 2 else 0
        platform_version = "15.0.0" if build >= 22000 else "10.0.0"
    except Exception:
        pass

    # Edge 版本（從 Chromium 版本推算，或直接抓 registry）
    edge_full = "154.0.8037.93"
    chrome_major = "154"
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Edge\BLBeacon",
            )
            edge_full, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            chrome_major = edge_full.split(".")[0]
        except Exception:
            pass

    return {
        "screen_width":          width,
        "screen_height":         height,
        "hardware_concurrency":  cpu_count,
        "device_memory":         mem_gb,
        "platform_version":      platform_version,
        "edge_full_version":     edge_full,
        "chrome_major":          chrome_major,
    }

# 啟動時執行一次，全程共用
REAL_FP = _get_real_fingerprint()

# UA 使用本機真實 Edge 版本
UA = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{REAL_FP['chrome_major']}.0.0.0 Safari/537.36 "
    f"Edg/{REAL_FP['chrome_major']}.0.0.0"
)

__all__ = [name for name in globals() if not name.startswith("__")]
