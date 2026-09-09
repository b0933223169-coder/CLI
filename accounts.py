"""Account storage and cookie/account migration."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *
from .security import *

class AccountManager:
    def __init__(self, path: Path = ACCOUNTS_FILE, cookie_dir: Path = COOKIE_DIR):
        self.path = path
        self.cookie_dir = cookie_dir
        self.accounts: list[dict] = []
        self._load()
        self._migrate_legacy()

    def _load(self):
        if self.path.exists():
            try:
                txt = self.path.read_text(encoding="utf-8")
                if not txt.strip():
                    self.accounts = []
                else:
                    self.accounts = json.loads(txt)
                    if not isinstance(self.accounts, list):
                        raise ValueError("accounts.json 頂層非 list")
            except Exception as e:
                try:
                    bak = self.path.with_suffix(f".bak.{int(datetime.now().timestamp())}.json")
                    shutil.copy2(self.path, bak)
                    note("WARN", f"accounts.json 讀取失敗（{e}），已備份至 {bak} 並重置")
                except Exception:
                    note("WARN", f"accounts.json 讀取失敗（{e}），已重置")
                self.accounts = []
        else:
            self.accounts = []

    def _save(self):
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self.accounts, ensure_ascii=False, indent=2)
        _atomic_write(self.path, data, 0o600)

    def _migrate_legacy(self):
        try:
            if self.path.resolve() != ACCOUNTS_FILE.resolve():
                return
        except Exception:
            if str(self.path) != str(ACCOUNTS_FILE):
                return
        if self.accounts or not LEGACY_COOKIE.exists():
            return
        try:
            COOKIE_DIR.mkdir(parents=True, exist_ok=True)
            migrated = COOKIE_DIR / "default.txt"
            if not migrated.exists():
                shutil.copy2(LEGACY_COOKIE, migrated)
                try:
                    migrated.chmod(0o600)
                except Exception:
                    pass
            try:
                rel = str(migrated.relative_to(_BASE))
            except Exception:
                rel = str(migrated)
            self.accounts.append({
                "name": "default", "email": "unknown (舊版遷移)",
                "cookie_file": rel, "created_at": datetime.now().isoformat(timespec="seconds"),
            })
            self._save()
            note("NOTICE", f"已自動遷移舊版 cookies.txt -> {migrated} (名稱: default)")
        except Exception as e:
            note("WARN", f"遷移舊 cookie 失敗: {e}")

    def list_accounts(self):
        return self.accounts

    def find(self, identifier: str):
        ident = identifier.strip().lower()
        for a in self.accounts:
            if a["name"].lower() == ident or a["email"].lower() == ident:
                return a
        return None

    def add_or_update(self, email: str, cookie_file: Path, name: str | None = None, password: str | None = None, user_id: str | None = None):
        email = email.strip()
        default_name = email.split("@")[0] if "@" in email else email
        name = (name or default_name).strip() or default_name
        existing = self.find(email)
        if existing:
            if name != existing["name"]:
                dup = self.find(name)
                if dup is not None and dup is not existing:
                    base = name
                    counter = 2
                    while self.find(name) is not None and self.find(name) is not existing:
                        name = f"{base}{counter}"
                        counter += 1
                    note("WARN", f"名稱衝突，已改為 {name}")
            try:
                rel = str(cookie_file.relative_to(_BASE))
            except Exception:
                try:
                    rel = str(cookie_file.relative_to(PROJECT_DIR))
                except Exception:
                    rel = str(cookie_file)
            existing["cookie_file"] = rel
            existing["last_login"] = datetime.now().isoformat(timespec="seconds")
            if name != default_name or existing["name"] == default_name:
                existing["name"] = name
            if password:
                try:
                    existing["password_enc"] = encrypt_password(password)
                    existing["password_len"] = len(password)
                except Exception as e:
                    note("WARN", f"密碼加密失敗：{e}")
            if user_id:
                existing["user_id"] = str(user_id)
            self._save()
            return existing
        base_name = name
        counter = 2
        while self.find(name):
            name = f"{base_name}{counter}"
            counter += 1
        try:
            _rel2 = str(cookie_file.relative_to(_BASE))
        except Exception:
            try:
                _rel2 = str(cookie_file.relative_to(PROJECT_DIR))
            except Exception:
                _rel2 = str(cookie_file)
        acc = {
            "name": name, "email": email, "cookie_file": _rel2,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_login": datetime.now().isoformat(timespec="seconds"),
        }
        if password:
            try:
                acc["password_enc"] = encrypt_password(password)
                acc["password_len"] = len(password)
            except Exception as e:
                note("WARN", f"密碼加密失敗：{e}")
        if user_id:
            acc["user_id"] = str(user_id)
        self.accounts.append(acc)
        self._save()
        return acc

    def rename(self, identifier: str, new_name: str):
        acc = self.find(identifier)
        if not acc:
            return None, f"找不到帳號: {identifier}"
        new_name = new_name.strip()
        if not new_name:
            return None, "新名稱不可為空"
        if re.search(r'[\/*?:"<>|\n\t]', new_name):
            return None, "新名稱包含不合法字元 (\\/*?:\"<>|)"
        if len(new_name) > 64:
            return None, "新名稱過長（>64）"
        dup = self.find(new_name)
        if dup is not None and dup is not acc:
            return None, f"名稱 '{new_name}' 已使用"
        old = acc["name"]
        acc["name"] = new_name
        self._save()
        return acc, old

    def remove(self, identifier: str):
        acc = self.find(identifier)
        if not acc:
            return False, f"找不到帳號: {identifier}"
        for base in [_BASE, PROJECT_DIR]:
            try:
                p = base / acc["cookie_file"]
                if not p.exists():
                    alt = Path(acc["cookie_file"])
                    if alt.exists():
                        p = alt
                if p.exists():
                    p.unlink()
                    break
            except Exception:
                continue
        self.accounts.remove(acc)
        self._save()
        return True, acc

    def get_cookie_path(self, identifier: str | None = None) -> Path | None:
        if not self.accounts:
            return None
        if identifier:
            acc = self.find(identifier)
            if not acc:
                return None
            p = PROJECT_DIR / acc["cookie_file"]
            try:
                p.resolve().relative_to(PROJECT_DIR.resolve())
            except Exception:
                note("WARN", f"帳號 {identifier} 的 cookie 路徑異常，已阻擋")
                return None
            return p
        def _ts(x):
            try:
                return datetime.fromisoformat(x.get("last_login",""))
            except Exception:
                return datetime.min
        sorted_acc = sorted(self.accounts, key=_ts, reverse=True)
        raw = sorted_acc[0]["cookie_file"]
        for base in [_BASE, PROJECT_DIR]:
            try:
                cand = (base / raw).resolve()
                if cand.exists() or True:
                    try:
                        cand.relative_to(base.resolve())
                        return cand
                    except Exception:
                        continue
            except Exception:
                continue
        p = PROJECT_DIR / raw
        try:
            p.resolve().relative_to(PROJECT_DIR.resolve())
        except Exception:
            note("WARN", "預設帳號 cookie 路徑異常")
            return None
        return p

    def get_account_for_cookie(self, cookie_path: Path):
        try:
            rel = str(cookie_path.relative_to(PROJECT_DIR)) if cookie_path.is_absolute() else str(cookie_path)
        except Exception:
            rel = str(cookie_path)
        for a in self.accounts:
            if a["cookie_file"] == rel or a["cookie_file"] == str(cookie_path):
                return a
        return None

__all__ = [name for name in globals() if not name.startswith("__")]
