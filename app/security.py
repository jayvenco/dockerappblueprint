from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="dab-session")
_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(("enc:" + settings.secret_key).encode()).digest()))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_session(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age_seconds)
    except BadSignature:
        return None
    return data.get("uid")


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        return ""


def new_api_token() -> tuple[str, str, str]:
    """Return (plain token, prefix, sha256 hash)."""
    plain = "dab_" + secrets.token_urlsafe(32)
    return plain, plain[:10], hash_token(plain)


def hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


class LoginLimiter:
    """In-memory brute-force protection: 5 failures per 5 minutes per client."""

    def __init__(self, max_fail: int = 5, window: int = 300):
        self.max_fail, self.window = max_fail, window
        self.fails: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        cutoff = time.time() - self.window
        self.fails[key] = [t for t in self.fails.get(key, []) if t > cutoff]
        return self.fails[key]

    def blocked(self, key: str) -> bool:
        return len(self._recent(key)) >= self.max_fail

    def fail(self, key: str) -> None:
        self._recent(key).append(time.time())

    def reset(self, key: str) -> None:
        self.fails.pop(key, None)


login_limiter = LoginLimiter()
