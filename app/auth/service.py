import random
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.security import hash_password, verify_password
from app.db.supabase_db import (
    clear_otp_code,
    create_user,
    get_user_by_email,
    save_otp_code,
)
from app.db.supabase_service import supabase

OTP_TTL_MINUTES = 5

# ── Константы защиты от брутфорса ─────────────────────────────────────────────
MAX_FAILED_LOGIN_ATTEMPTS = 5       # после 5 неудачных попыток — блок
LOCKOUT_DURATION_MINUTES  = 15      # блок на 15 минут
MAX_OTP_ATTEMPTS          = 3       # 3 попытки OTP, потом сброс
LOGIN_SESSION_TTL_MINUTES = 5       # временный токен живёт 5 минут


# ═══════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def generate_device_id() -> str:
    return str(uuid4())


def generate_otp_code() -> str:
    return f"{random.randint(100000, 999999)}"


def hash_otp(otp_code: str) -> str:
    """
    OTP хранится в БД хэшированным.
    Если БД утечёт — открытые OTP коды не скомпрометированы.
    SHA-256 достаточно: OTP короткоживущий (5 мин) и одноразовый.
    """
    return hashlib.sha256(otp_code.encode()).hexdigest()


def generate_login_session_token() -> str:
    """
    Временный непрозрачный токен для связи шагов MFA.
    НЕ JWT — намеренно. JWT можно декодировать на клиенте,
    а этот токен — просто случайный UUID, смысл которого знает только сервер.
    """
    return str(uuid4())


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАЩИТА ОТ БРУТФОРСА
# ═══════════════════════════════════════════════════════════════════════════════

def check_account_lockout(user: dict) -> tuple[bool, str | None]:
    """
    Проверяет заблокирован ли аккаунт.
    Возвращает (is_locked, error_message).

    Логика:
    - Если failed_login_attempts >= MAX → смотрим когда была последняя попытка
    - Если прошло меньше LOCKOUT_DURATION → аккаунт заблокирован
    - Если прошло больше → автоматически сбрасываем счётчик
    """
    attempts = user.get("failed_login_attempts", 0)
    last_failed_at_raw = user.get("last_failed_at")

    if attempts < MAX_FAILED_LOGIN_ATTEMPTS:
        return False, None  # не заблокирован

    if not last_failed_at_raw:
        return False, None

    last_failed_at = datetime.fromisoformat(
        str(last_failed_at_raw).replace("Z", "+00:00")
    )
    lockout_until = last_failed_at + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

    if datetime.now(timezone.utc) < lockout_until:
        remaining = int((lockout_until - datetime.now(timezone.utc)).total_seconds() / 60)
        return True, f"Account locked. Try again in {remaining} minutes."

    # Блокировка истекла — сбрасываем счётчик
    _reset_failed_attempts(user["id"])
    return False, None


def record_failed_login(user_id: str) -> None:
    """Инкрементируем счётчик неудачных попыток."""
    supabase.table("users").update({
        "failed_login_attempts": supabase.raw("failed_login_attempts + 1"),
        "last_failed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", user_id).execute()


def _reset_failed_attempts(user_id: str) -> None:
    """Сбрасываем счётчик после успешного логина или истечения блокировки."""
    supabase.table("users").update({
        "failed_login_attempts": 0,
        "last_failed_at": None,
    }).eq("id", user_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN SESSION (временный токен между шагами MFA)
# ═══════════════════════════════════════════════════════════════════════════════

def create_login_session(user_id: str, device_id: str, purpose: str) -> str:
    """
    Создаёт временную запись в login_sessions.
    purpose: 'registration' или 'login'

    Эта таблица нужна чтобы:
    1. Связать шаг 1 (пароль) с шагом 2 (OTP) без выдачи реальных токенов
    2. Хранить состояние на сервере (клиент не может подделать)
    3. Ограничить время жизни MFA-сессии
    """
    token = generate_login_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_SESSION_TTL_MINUTES)

    # Удаляем старые незавершённые сессии для этого устройства
    supabase.table("login_sessions").delete().eq("user_id", user_id).eq("device_id", device_id).execute()

    supabase.table("login_sessions").insert({
        "token": token,
        "user_id": user_id,
        "device_id": device_id,
        "purpose": purpose,
        "otp_attempts": 0,
        "expires_at": expires_at.isoformat(),
    }).execute()

    return token


def get_login_session(token: str) -> dict | None:
    """Находим и валидируем временную MFA-сессию."""
    result = (
        supabase.table("login_sessions")
        .select("*")
        .eq("token", token)
        .execute()
    )
    if not result.data:
        return None

    session = result.data[0]
    expires_at = datetime.fromisoformat(
        str(session["expires_at"]).replace("Z", "+00:00")
    )
    if datetime.now(timezone.utc) > expires_at:
        # Сессия истекла — удаляем
        supabase.table("login_sessions").delete().eq("token", token).execute()
        return None

    return session


def consume_login_session(token: str) -> None:
    """Удаляем временную сессию после успешного OTP (одноразовая)."""
    supabase.table("login_sessions").delete().eq("token", token).execute()


def increment_otp_attempts(session_token: str, current_attempts: int) -> bool:
    """
    Увеличиваем счётчик попыток OTP.
    Возвращает True если лимит превышен → нужно аннулировать сессию.
    """
    new_attempts = current_attempts + 1
    if new_attempts >= MAX_OTP_ATTEMPTS:
        # Удаляем сессию — пользователь должен начать логин заново
        consume_login_session(session_token)
        return True  # лимит превышен

    supabase.table("login_sessions").update({
        "otp_attempts": new_attempts
    }).eq("token", session_token).execute()
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНЫЕ СЕРВИСНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def register_user(email: str, password: str, device_id: str) -> dict:
    if get_user_by_email(email):
        raise ValueError("User already exists")
    return create_user(email, hash_password(password), device_id)


def authenticate_user(email: str, password: str) -> tuple[dict | None, str | None]:
    """
    Возвращает (user, error).
    Намеренно не говорим клиенту что именно неверно (email или пароль) —
    это предотвращает user enumeration атаку.
    """
    user = get_user_by_email(email)

    # Проверяем блокировку ДО проверки пароля
    if user:
        is_locked, lock_error = check_account_lockout(user)
        if is_locked:
            return None, lock_error

    # Проверяем пароль
    if not user or not verify_password(password, user["password_hash"]):
        # Записываем неудачную попытку (только если пользователь существует)
        if user:
            record_failed_login(user["id"])
        # Одинаковое сообщение для "нет такого юзера" и "неверный пароль"
        return None, "Invalid credentials"

    # Успешный логин — сбрасываем счётчик
    _reset_failed_attempts(user["id"])
    return user, None


def issue_otp_for_user(user_id: str) -> str:
    """Генерируем OTP и сохраняем его ХЭШИРОВАННЫМ."""
    otp_code = generate_otp_code()
    otp_hash = hash_otp(otp_code)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    save_otp_code(user_id, otp_hash, expires_at.isoformat())  # сохраняем хэш!
    return otp_code  # возвращаем чистый код только для отправки на email


def verify_user_otp(email: str, otp_code: str) -> tuple[dict | None, str | None]:
    """Проверяем OTP сравнивая хэши."""
    user = get_user_by_email(email)
    if not user:
        return None, "User not found"

    stored_hash   = user.get("otp_code")
    expires_at_raw = user.get("otp_code_expire_time")

    if not stored_hash or not expires_at_raw:
        return None, "OTP not requested"

    # Хэшируем входящий код и сравниваем с хранимым хэшем
    if stored_hash != hash_otp(otp_code):
        return None, "Invalid OTP code"

    expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        return None, "OTP code expired"

    clear_otp_code(user["id"])
    return user, None