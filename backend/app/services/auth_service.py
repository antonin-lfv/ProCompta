import base64
import hashlib
import hmac
import json
import secrets
import time

_SESSION_MAX_AGE = 30 * 24 * 3600  # 30 jours


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, dk_hex = hashed.split("$", 1)
        dk = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def _sign(data: str, key: str) -> str:
    h = hmac.new(key.encode(), data.encode(), hashlib.sha256)
    return base64.urlsafe_b64encode(h.digest()).decode().rstrip("=")


def create_token(user_id: str, secret: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"uid": str(user_id), "exp": int(time.time()) + _SESSION_MAX_AGE}).encode()
    ).decode()
    return f"{payload}.{_sign(payload, secret)}"


def verify_token(token: str, secret: str) -> str | None:
    try:
        payload, sig = token.rsplit(".", 1)
        if not secrets.compare_digest(sig, _sign(payload, secret)):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
        if data["exp"] < time.time():
            return None
        return data["uid"]
    except Exception:
        return None
