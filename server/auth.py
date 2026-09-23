"""V2HTML 服务端 · 管理后台认证（PBKDF2 凭据 + HMAC 签名会话 Cookie）。"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from . import store


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return salt, h.hex()


def verify_password(password: str, salt: str, expected: str) -> bool:
    _, h = hash_password(password, salt)
    return hmac.compare_digest(h, expected)


def set_credentials(username: str, password: str) -> None:
    salt, h = hash_password(password)
    cfg = store.load()
    cfg["admin"] = {"username": username, "salt": salt, "hash": h}
    store.save(cfg)


def verify_credentials(username: str, password: str) -> bool:
    admin = store.load().get("admin") or {}
    if not admin or username != admin.get("username"):
        return False
    return verify_password(password, admin["salt"], admin["hash"])


def _secret() -> str:
    cfg = store.load()
    if not cfg.get("session_secret"):
        cfg["session_secret"] = secrets.token_hex(32)
        store.save(cfg)
    return cfg["session_secret"]


def make_session(username: str, days: int = 7) -> str:
    exp = int(time.time()) + days * 86400
    msg = f"{username}.{exp}"
    sig = hmac.new(_secret().encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def check_session(token: str | None) -> str | None:
    """返回用户名；无效返回 None。"""
    if not token:
        return None
    try:
        username, exp, sig = token.rsplit(".", 2)[-3:] if token.count(".") >= 2 else ("", "", "")
        parts = token.split(".")
        username, exp, sig = parts[0], parts[1], ".".join(parts[2:])
        if int(exp) < time.time():
            return None
        msg = f"{username}.{exp}"
        good = hmac.new(_secret().encode(), msg.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, good):
            return username
    except Exception:
        pass
    return None
