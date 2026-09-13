"""Cookie serialization and local password protection."""
from __future__ import annotations
from ._compat import *
from .paths import *
from .colors import *

def save_netscape_cookies(cookies, path: Path):
    lines = ["# Netscape HTTP Cookie File", "# 由 cool.py 自動產生，請勿分享此檔案"]
    for c in cookies:
        domain = str(c.get("domain","")).replace("\t"," ").replace("\n"," ").strip() or "coolenglish.edu.tw"
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path_ = str(c.get("path", "/")).replace("\t"," ").replace("\n"," ").strip() or "/"
        secure = "TRUE" if c.get("secure") else "FALSE"
        try:
            exp_raw = c.get("expires", -1)
            expiry = str(int(exp_raw)) if exp_raw and int(exp_raw) > 0 else "0"
        except Exception:
            expiry = "0"
        name = str(c.get("name","")).replace("\t"," ").replace("\n"," ").replace(" ","_").strip()
        value = str(c.get("value","")).replace("\t"," ").replace("\n"," ").strip()
        if not name:
            continue
        lines.append(f"{domain}\t{flag}\t{path_}\t{secure}\t{expiry}\t{name}\t{value}")
    data = "\n".join(lines) + "\n"
    _atomic_write(path, data, 0o600)

def _machine_key() -> bytes:
    mid = None
    for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        try:
            mid = Path(p).read_text(encoding="utf-8").strip()
            if mid:
                break
        except Exception:
            continue
    if not mid:
        try:
            import uuid, socket
            mid = f"{socket.gethostname()}-{uuid.getnode()}"
        except Exception:
            mid = "fallback-machine-id"
        note("WARN", "無法讀取 machine-id，已使用主機退化鍵（跨機器無法解密）")
    return hashlib.sha256((mid + "cool_salt_v1").encode()).digest()

def encrypt_password(pwd: str) -> str:
    if not isinstance(pwd, str):
        raise TypeError("密碼需為字串")
    if len(pwd) > 1024:
        raise ValueError("密碼過長")
    key = _machine_key()
    enc = bytes(b ^ key[i % len(key)] for i, b in enumerate(pwd.encode("utf-8")))
    return base64.b64encode(enc).decode("utf-8")

def decrypt_password(enc: str) -> str:
    key = _machine_key()
    try:
        data = base64.b64decode(enc.encode("utf-8"), validate=True)
    except Exception as e:
        raise ValueError(f"base64 解碼失敗: {e}")
    dec = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    try:
        return dec.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"解密後非 utf-8（可能 machine-id 已變更）: {e}")

_COOL_SUDO_AUTH = False

def _hash_passwd(pwd: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, 200000)
    return f"{salt.hex()}${dk.hex()}"

def has_cool_passwd() -> bool:
    return PASSWD_FILE.exists()

def set_cool_passwd(pwd: str):
    data = _hash_passwd(pwd)
    _atomic_write(PASSWD_FILE, data, 0o600)

def verify_cool_passwd(pwd: str) -> bool:
    if not PASSWD_FILE.exists():
        return False
    try:
        raw = PASSWD_FILE.read_text(encoding="utf-8").strip()
        if "$" not in raw:
            return secrets.compare_digest(raw, hashlib.sha256(pwd.encode("utf-8")).hexdigest())
        salt_hex, hash_hex = raw.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = _hash_passwd(pwd, salt)
        return secrets.compare_digest(raw, expected)
    except Exception:
        return False

def has_sudo() -> bool:
    global _COOL_SUDO_AUTH
    if _COOL_SUDO_AUTH:
        return True
    if not has_cool_passwd():
        note("WARN", "尚未設定 cool passwd，請先執行 cool passwd 設定 sudo 密碼")
        return False
    try:
        pwd = getpass.getpass("請輸入 cool sudo 密碼: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if verify_cool_passwd(pwd):
        _COOL_SUDO_AUTH = True
        return True
    note("ERR", "cool sudo 密碼錯誤")
    return False

def has_sudo_cached() -> bool:
    return _COOL_SUDO_AUTH

def reset_sudo():
    global _COOL_SUDO_AUTH
    _COOL_SUDO_AUTH = False

def get_stored_password(acc: dict) -> str | None:
    enc = acc.get("password_enc")
    if not enc:
        return None
    if not has_sudo():
        note("WARN", "未取得 cool sudo 權限，無法自動使用已儲存密碼，將改為手動輸入")
        return None
    try:
        return decrypt_password(enc)
    except Exception as e:
        note("WARN", f"解密失敗：{e}")
        return None

def cmd_passwd(mgr, args: list[str]):
    if has_cool_passwd():
        note("INFO", "已存在 cool passwd，將覆蓋設定")
        try:
            old = getpass.getpass("請輸入舊 cool sudo 密碼 (直接 Enter 跳過驗證): ")
        except (EOFError, KeyboardInterrupt):
            print()
            note("INFO", "已取消")
            return
        if old and not verify_cool_passwd(old):
            note("ERR", "舊密碼錯誤，已取消")
            return
    try:
        pwd1 = getpass.getpass("設定新的 cool sudo 密碼: ")
        if not pwd1:
            note("WARN", "密碼不可為空，已取消")
            return
        pwd2 = getpass.getpass("確認密碼: ")
        if pwd1 != pwd2:
            note("ERR", "兩次輸入不一致，已取消")
            return
        set_cool_passwd(pwd1)
        global _COOL_SUDO_AUTH
        _COOL_SUDO_AUTH = True
        note("INFO", "cool passwd 設定完成，已自動取得 sudo 權限")
    except (EOFError, KeyboardInterrupt):
        print()
        note("INFO", "已取消")

__all__ = [name for name in globals() if not name.startswith("__")]
