from uuid import uuid4
from app.db.supabase_service import supabase

def create_user(email: str, password_hash: str, device_id: str):
    user = {
        "id": str(uuid4()),
        "email": email,
        "password_hash": password_hash,
        "device_id": device_id,
        "otp_code": None,
        "otp_code_expire_time": None,
    }

    result = supabase.table("users").insert(user).execute()
    return result.data[0]

def get_user_by_email(email: str):
    result = (
        supabase
        .table("users")
        .select("*")
        .eq("email", email)
        .execute()
    )
    return result.data[0] if result.data else None

def save_device_id(user_id: str, device_id: str):
    result = (
        supabase.table("users")
        .update({"device_id": device_id}) \
        .eq("id", user_id) \
        .execute()
    )
    return result.data[0] if result.data else None

def save_otp_code(user_id: str, otp_code: str, otp_code_expire_time: str):
    result = (
        supabase.table("users")
        .update({
            "otp_code": otp_code,
            "otp_code_expire_time": otp_code_expire_time,
        })
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None

def clear_otp_code(user_id: str):
    result = (
        supabase.table("users")
        .update({
            "otp_code": None,
            "otp_code_expire_time": None,
        })
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None
