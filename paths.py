"""Project and persistent-data paths."""
from __future__ import annotations
from ._compat import *

BASE_URL = "https://www.coolenglish.edu.tw"
LOGIN_URL = f"{BASE_URL}/login/index.php"
DEFAULT_TARGET = f"{BASE_URL}/time/time_view_detail_by_people.php?id=2055519"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

PROJECT_DIR = Path(__file__).resolve().parent.parent

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

__all__ = [name for name in globals() if not name.startswith("__")]
