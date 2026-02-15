import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.supabase_db import (
    clear_otp_code,
    create_user,
    get_user_by_email,
    save_otp_code,
)
from app.core.security import hash_password, verify_password

OTP_TTL_MINUTES = 5

def generate_device_id() -> str:
    return str(uuid4())

def generate_otp_code() -> str:
    return f"{random.randint(100000, 999999)}"

def register_user(email: str, password: str, device_id: str | None = None):
    if get_user_by_email(email):
        raise ValueError("User already exists")
    user_device_id = device_id or generate_device_id()
    return create_user(email, hash_password(password), user_device_id)

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user

def issue_otp_for_user(user_id: str):
    otp_code = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    save_otp_code(user_id, otp_code, expires_at.isoformat())
    return otp_code

def verify_user_otp(email: str, otp_code: str):
    user = get_user_by_email(email)
    if not user:
        return None, "User not found"

    stored_code = user.get("otp_code")
    expires_at_raw = user.get("otp_code_expire_time")

    if not stored_code or not expires_at_raw:
        return None, "OTP not requested"

    if stored_code != otp_code:
        return None, "Invalid OTP code"

    expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        return None, "OTP code expired"

    clear_otp_code(user["id"])
    return user, None
