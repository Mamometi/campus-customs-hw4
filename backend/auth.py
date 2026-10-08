"""Password hashing and signed login tokens (stdlib only).

Hashes use the format already in the users table: pbkdf2_sha256$<salt>$<hex digest>.
The iteration count is not stored in the hash (open question #1 in harness.md),
so it is configurable via PBKDF2_ITERATIONS.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "600000"))
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def _secret() -> bytes:
    key = os.getenv("SECRET_KEY")
    if not key or key.startswith("replace-with"):
        raise RuntimeError("SECRET_KEY is not set (see backend/.env.example)")
    return key.encode()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, _ = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user_id: int) -> str:
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str) -> int | None:
    try:
        payload, sig = token.split(".")
    except ValueError:
        return None
    expected = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    data = json.loads(_unb64(payload))
    if data.get("exp", 0) < time.time():
        return None
    return int(data["uid"])
