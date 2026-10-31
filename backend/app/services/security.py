import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from app.core.config import settings


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${hashed.hex()}"


def verify_password(password: str, stored_value: str) -> bool:
    try:
        salt, _ = stored_value.split("$", 1)
        expected_value = hash_password(password, salt)
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(expected_value, stored_value)


def create_token(user_id: int, version: int = 0) -> str:
    if not settings.secret_key: raise RuntimeError("请先设置账号保护值 SECRET_KEY")
    now = int(time.time())
    payload = {"user_id": user_id, "version": version, "iat": now, "exp": now + 7 * 86400, "nonce": secrets.token_hex(12)}
    payload_text = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.secret_key.encode(), payload_text.encode(), hashlib.sha256).hexdigest()
    return f"{payload_text}.{signature}"


def read_token(token: str):
    if not settings.secret_key:
        return None
    try:
        payload_text, signature = token.rsplit(".", 1)
        expected = hmac.new(settings.secret_key.encode(), payload_text.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_text + "=" * (-len(payload_text) % 4)))
        if int(payload.get("exp", 0)) <= time.time() or int(payload.get("iat", 0)) > time.time() + 60:
            return None
        payload["user_id"] = int(payload["user_id"])
        return payload
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeError):
        return None


def read_token_user_id(token: str) -> Optional[int]:
    payload = read_token(token)
    return payload["user_id"] if payload else None
