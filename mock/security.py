# mock/security.py
"""掩码 / 令牌 / 员工 JWT / Webhook HMAC-SHA256。全部只处理合成数据。"""
import base64
import hashlib
import hmac
import json
import secrets
import time

HMAC_SECRET = "clawhunt-1807-mock-hmac-secret"
JWT_SECRET = "clawhunt-1807-mock-jwt-secret"
VAULT_PERMISSION = "vault:read"


def mask_phone(value: str) -> str:
    """手机号掩码：138****8000（契约口径）。"""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) < 7:
        return "*" * max(len(digits), 1)
    return digits[:3] + "****" + digits[-4:]


def mask_name(value: str) -> str:
    """姓名掩码：王**（契约口径）。"""
    text = str(value).strip()
    if not text:
        return "**"
    if len(text) <= 1:
        return text + "**"
    return text[0] + "*" * (len(text) - 1)


def new_token(prefix: str) -> str:
    return prefix + secrets.token_hex(16)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def issue_employee_jwt(employee_id: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": employee_id,
        "role": "employee",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    head = _b64url(json.dumps(header, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{head}.{body}".encode()
    sig = _b64url(hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def verify_employee_jwt(token: str) -> dict | None:
    try:
        head, body, sig = token.split(".")
        expected = _b64url(
            hmac.new(JWT_SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, KeyError):
        return None


def hmac_signature(body_text: str, timestamp_ms: int, secret: str = HMAC_SECRET) -> str:
    """契约：HMAC-SHA256(secret, f"{timestamp_ms}.{raw_json_body}")。"""
    mac = hmac.new(secret.encode(), f"{timestamp_ms}.{body_text}".encode(), hashlib.sha256)
    return mac.hexdigest()
