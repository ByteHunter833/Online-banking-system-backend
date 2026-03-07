from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    OtpVerifyRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
)
from app.auth.service import (
    authenticate_user,
    create_login_session,
    get_login_session,
    consume_login_session,
    increment_otp_attempts,
    issue_otp_for_user,
    register_user,
    verify_user_otp,
)
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    validate_refresh_token,
)
from app.db.supabase_service import supabase
from app.db.supabase_db import _audit_log, clear_specific_device
from app.service.email_service import send_otp_code

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Вспомогательная функция аудит лога ────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=MessageResponse)
async def register(data: RegisterRequest, request: Request):
    """
    Шаг 1 регистрации:
    - Создаём пользователя (is_active=False)
    - Отправляем OTP на email
    - Возвращаем login_session_token для следующего шага

    После этого клиент должен вызвать /verify-otp с этим токеном.
    """
    try:
        user = register_user(data.email, data.password, data.device_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # OTP хранится хэшированным в БД
    otp_code = issue_otp_for_user(user["id"])
    await send_otp_code(user["email"], otp_code)

    # Создаём временную MFA-сессию (живёт 5 минут)
    session_token = create_login_session(
        user_id=user["id"],
        device_id=data.device_id,
        purpose="registration",
    )

    _audit_log("register_initiated", request, user_id=user["id"], device_id=data.device_id)

    return {
        "message": "Registered. OTP sent to your email.",
        "login_session_token": session_token,   # нужен для /verify-otp
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ЛОГИН — Шаг 1: пароль
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/login", response_model=MessageResponse)
async def login(data: LoginRequest, request: Request):
    """
    Шаг 1 логина:
    - Проверяем email + password
    - Проверяем не заблокирован ли аккаунт
    - Если всё ОК — отправляем OTP и возвращаем login_session_token
    - Финальные токены НЕ выдаём — пользователь ещё не прошёл 2FA

    Такой flow (password → OTP → tokens) обязателен для банка.
    """
    user, error = authenticate_user(data.email, data.password)

    if error or not user:
        _audit_log(
            "login_failed",
            request,
            details=f"email={data.email}, reason={error}",
        )
        # Одинаковое сообщение — не раскрываем причину
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("is_active"):
        raise HTTPException(
            status_code=403,
            detail="Account not verified. Check your email."
        )

    # Отправляем OTP для 2FA
    otp_code = issue_otp_for_user(user["id"])
    await send_otp_code(user["email"], otp_code)

    # Создаём временную MFA-сессию
    session_token = create_login_session(
        user_id=user["id"],
        device_id=data.device_id,
        purpose="login",
    )

    _audit_log("login_otp_sent", request, user_id=user["id"], device_id=data.device_id)

    return {
        "message": "Password accepted. OTP sent to your email.",
        "login_session_token": session_token,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OTP ВЕРИФИКАЦИЯ — Шаг 2: второй фактор
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(data: OtpVerifyRequest, request: Request):
    """
    Шаг 2 (финальный) для регистрации и логина.
    Только здесь выдаются реальные access + refresh токены.

    Защиты:
    - login_session_token одноразовый и живёт 5 минут
    - Максимум 3 попытки OTP, потом сессия аннулируется
    - Устройство берётся из сессии (нельзя подменить)
    - Все попытки логируются
    """
    # 1. Валидируем временную MFA-сессию
    session = get_login_session(data.login_session_token)
    if not session:
        raise HTTPException(
            status_code=400,
            detail="Session expired or invalid. Please login again."
        )

    user_id   = session["user_id"]
    device_id = session["device_id"]  # берём device_id из СЕССИИ, не от клиента

    # 2. Получаем пользователя по user_id из сессии
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = result.data[0]

    # 3. Проверяем OTP (сравниваем хэши)
    _, error = verify_user_otp(user["email"], data.otp_code)
    if error:
        # Увеличиваем счётчик попыток
        limit_exceeded = increment_otp_attempts(
            data.login_session_token,
            session["otp_attempts"]
        )
        _audit_log(
            "otp_failed",
            request,
            user_id=user_id,
            device_id=device_id,
            details=f"reason={error}, attempts={session['otp_attempts']+1}, limit_exceeded={limit_exceeded}",
        )
        if limit_exceeded:
            raise HTTPException(
                status_code=429,
                detail="Too many OTP attempts. Please login again."
            )
        raise HTTPException(status_code=400, detail=error)

    # 4. OTP верный — сессия одноразовая, удаляем её
    consume_login_session(data.login_session_token)

    # 5. Если это регистрация — активируем аккаунт
    if session["purpose"] == "registration":
        supabase.table("users").update({"is_active": True}).eq("id", user_id).execute()

    # 6. Создаём токены, привязанные к device_id
    access_token  = create_access_token(user_id, device_id)
    refresh_token = create_refresh_token(user_id, device_id)

    # 7. Сохраняем сессию (upsert требует UNIQUE(user_id, device_id) в БД)
    supabase.table("user_sessions").upsert({
        "user_id":       user_id,
        "device_id":     device_id,
        "refresh_token": refresh_token,
        "last_login":    "now()",
    }, on_conflict="user_id,device_id").execute()

    _audit_log(
        "login_success",
        request,
        user_id=user_id,
        device_id=device_id,
        details=f"purpose={session['purpose']}",
    )

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "message": "Authentication successful.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/logout", response_model=MessageResponse)
def logout(data: LogoutRequest, request: Request, user=Depends(get_current_user)):
    """
    Удаляем сессию только для этого устройства.
    Остальные устройства (телефон, планшет) продолжают работать.
    """
    clear_specific_device(user["id"], data.device_id)
    _audit_log("logout", request, user_id=user["id"], device_id=data.device_id)
    return {"message": "Logged out successfully from this device"}


# ═══════════════════════════════════════════════════════════════════════════════
# REFRESH TOKEN ROTATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    token_data: tuple = Depends(validate_refresh_token),
):
    """
    Refresh Token Rotation:
    1. Validate_refresh_token проверяет подпись И наличие токена в БД
    2. Выдаём новую пару токенов
    3. Старый refresh_token заменяется в БД → повторное использование невозможно

    Если кто-то попытается использовать уже ротированный токен — получит 401.
    Это детектирует кражу токена.
    """
    user_id, device_id, old_refresh_token = token_data

    new_access  = create_access_token(user_id, device_id)
    new_refresh = create_refresh_token(user_id, device_id)

    # Обновляем ТОЛЬКО ту сессию где совпадает старый токен
    result = (
        supabase.table("user_sessions")
        .update({"refresh_token": new_refresh, "last_login": "now()"})
        .eq("user_id",       user_id)
        .eq("device_id",     device_id)
        .eq("refresh_token", old_refresh_token)  # точное совпадение со старым токеном
        .execute()
    )

    if not result.data:
        # Если update ничего не нашёл — токен уже был ротирован.
        # Возможная атака с украденным токеном — логируем!
        _audit_log(
            "refresh_token_reuse_detected",
            request,
            user_id=user_id,
            device_id=device_id,
            details="Possible token theft detected",
        )
        raise HTTPException(
            status_code=401,
            detail="Token already used. Please login again."
        )

    return {"access_token": new_access, "refresh_token": new_refresh}


# ═══════════════════════════════════════════════════════════════════════════════
# СЛУЖЕБНЫЕ
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users/me")
def get_me(user=Depends(get_current_user)):
    return {
        "id":         user["id"],
        "email":      user["email"],
        "created_at": user["created_at"],
    }


@router.get("/health-check")
async def health_check():
    return "OK"