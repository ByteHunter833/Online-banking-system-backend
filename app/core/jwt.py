from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import settings
from app.db.supabase_db import get_user_by_id
from app.db.supabase_service import supabase

# ── Настройки ──────────────────────────────────────────────────────────────────
# SECRET_KEY берётся из переменных окружения через settings
# В .env: SECRET_KEY=<минимум 32 случайных символа>
SECRET_KEY = settings.SECRET_KEY
ALGORITHM  = "HS256"

security = HTTPBearer()


# ═══════════════════════════════════════════════════════════════════════════════
# СОЗДАНИЕ ТОКЕНОВ
# ═══════════════════════════════════════════════════════════════════════════════

def create_access_token(user_id: str, device_id: str) -> str:
    """
    Access token привязан к device_id.
    Если токен украдут и попытаются использовать с другого устройства — он не подойдёт.
    Живёт 15 минут.
    """
    payload = {
        "sub":        user_id,
        "device_id":  device_id,     # привязка к устройству
        "token_type": "access",
        "exp":        datetime.now(timezone.utc) + timedelta(minutes=15),
        "iat":        datetime.now(timezone.utc),  # issued at — для аудита
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, device_id: str) -> str:
    """
    Refresh token тоже привязан к device_id.
    Живёт 7 дней. Хранится в БД — можно отозвать.
    """
    payload = {
        "sub":        user_id,
        "device_id":  device_id,
        "token_type": "refresh",
        "exp":        datetime.now(timezone.utc) + timedelta(days=7),
        "iat":        datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ═══════════════════════════════════════════════════════════════════════════════
# ВАЛИДАЦИЯ ТОКЕНОВ
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Dependency для защищённых эндпоинтов.
    Проверяет:
    1. Подпись JWT
    2. Тип токена (должен быть access)
    3. Что пользователь существует в БД
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("token_type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id   = payload.get("sub")
        device_id = payload.get("device_id")

        if not user_id or not device_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Прокидываем device_id в объект пользователя — нужен в logout и аудите
    user["current_device_id"] = device_id
    return user


def validate_refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> tuple[str, str, str]:
    """
    Валидация refresh token в два этапа:

    1. Проверка подписи JWT → гарантирует что токен не подделан
    2. Проверка наличия токена в БД → гарантирует что:
       - Токен не был отозван через logout
       - Токен не был уже использован (rotation)

    Возвращает (user_id, device_id, raw_token) для ротации в роутере.
    """
    token = credentials.credentials

    # Этап 1: JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Use refresh token here")

        user_id   = payload.get("sub")
        device_id = payload.get("device_id")

        if not user_id or not device_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")

    # Этап 2: Проверка в БД
    # Ищем сессию где совпадают user_id + device_id + refresh_token
    result = (
        supabase.table("user_sessions")
        .select("device_id")
        .eq("user_id",        user_id)
        .eq("device_id",      device_id)
        .eq("refresh_token",  token)
        .execute()
    )

    if not result.data:
        # Возможные причины:
        # - Пользователь разлогинился (сессия удалена)
        # - Токен уже был ротирован (повторное использование старого токена!)
        raise HTTPException(
            status_code=401,
            detail="Session not found. Please login again."
        )

    return user_id, device_id, token