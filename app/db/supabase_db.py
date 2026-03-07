from urllib.request import Request
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
def get_user_by_id(user_id: str):
    result = (
        supabase
        .table("users")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return result.data

def clear_specific_device(user_id: str, device_id: str):
    """Удаляет конкретную сессию (device_id) для пользователя. Используется в logout."""
    supabase.table("user_sessions").delete().eq("user_id", user_id).eq("device_id", device_id).execute()


def _audit_log(
    event: str,
    request: Request,
    user_id: str | None = None,
    device_id: str | None = None,
    details: str | None = None,
) -> None:
    """
    Пишем каждое важное событие в audit_log.
    В банке это обязательно — для расследования инцидентов.
    Пишем асинхронно в фоне чтобы не замедлять ответ.
    """
    try:
        supabase.table("audit_log").insert({
            "event":     event,
            "user_id":   user_id,
            "device_id": device_id,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "details":   details,
        }).execute()
    except Exception:
        pass  # Аудит не должен ронять основной запрос
