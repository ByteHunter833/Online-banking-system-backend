from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from struct import pack
from urllib.parse import quote

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _normalize_secret(secret: str) -> str:
    # Keep a stable normalization layer so existing hashing/verification logic
    # stays consistent even if the underlying password scheme changes.
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_secret(password))


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_secret(password), hashed_password)


def validate_password_strength(password: str) -> None:
    checks = {
        "at least 8 characters": len(password) >= 8,
        "one uppercase letter": any(character.isupper() for character in password),
        "one lowercase letter": any(character.islower() for character in password),
        "one digit": any(character.isdigit() for character in password),
        "one special character": any(
            character in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for character in password
        ),
    }
    errors = [label for label, passed in checks.items() if not passed]
    if errors:
        raise ValueError(f"Password must contain {', '.join(errors)}.")


def create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    device_id: str | None = None,
    roles: list[str] | None = None,
    jti: str | None = None,
    family_id: str | None = None,
    session_id: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "token_type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if device_id:
        payload["device_id"] = device_id
    if roles:
        payload["roles"] = roles
    if jti:
        payload["jti"] = jti
    if family_id:
        payload["family_id"] = family_id
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str,
    roles: list[str],
    device_id: str | None = None,
    session_id: str | None = None,
) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        device_id=device_id,
        roles=roles,
        session_id=session_id,
    )


def create_refresh_token(
    *,
    subject: str,
    device_id: str | None,
    jti: str,
    family_id: str,
    session_id: str | None = None,
) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        device_id=device_id,
        jti=jti,
        family_id=family_id,
        session_id=session_id,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Token is invalid or expired.") from exc


def generate_jti() -> str:
    return secrets.token_urlsafe(24)


def generate_numeric_otp(length: int = 6) -> str:
    digits = "".join(secrets.choice("0123456789") for _ in range(length))
    return digits


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_base32_secret(length: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(length)).decode("utf-8").rstrip("=")


def generate_totp_code(
    secret_base32: str,
    *,
    at_time: datetime | None = None,
    period_seconds: int = 30,
    digits: int = 6,
) -> str:
    now = at_time or datetime.now(timezone.utc)
    padded_secret = secret_base32 + "=" * ((8 - len(secret_base32) % 8) % 8)
    key = base64.b32decode(padded_secret, casefold=True)
    counter = int(now.timestamp()) // period_seconds
    digest = hmac.new(key, pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    )
    return str(binary % (10 ** digits)).zfill(digits)


def verify_totp_code(
    secret_base32: str,
    code: str,
    *,
    at_time: datetime | None = None,
    period_seconds: int = 30,
    digits: int = 6,
    allowed_drift_steps: int = 1,
) -> bool:
    now = at_time or datetime.now(timezone.utc)
    for delta in range(-allowed_drift_steps, allowed_drift_steps + 1):
        candidate_time = now + timedelta(seconds=delta * period_seconds)
        if generate_totp_code(
            secret_base32,
            at_time=candidate_time,
            period_seconds=period_seconds,
            digits=digits,
        ) == code:
            return True
    return False


def build_totp_uri(secret_base32: str, account_name: str, issuer: str | None = None) -> str:
    safe_issuer = issuer or settings.totp_issuer
    label = quote(f"{safe_issuer}:{account_name}")
    return (
        f"otpauth://totp/{label}"
        f"?secret={secret_base32}&issuer={quote(safe_issuer)}&algorithm=SHA1&digits=6&period=30"
    )


def generate_recovery_codes(count: int = 6) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def ip_fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return hash_token(value)
