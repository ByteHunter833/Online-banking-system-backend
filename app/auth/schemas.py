from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str        # UUID генерируется на клиенте один раз и хранится локально
    device_name: str      # "iPhone 15 Pro", "Chrome on Windows"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """В банке обязателен сильный пароль."""
        errors = []
        if len(v) < 8:
            errors.append("минимум 8 символов")
        if not re.search(r"[A-Z]", v):
            errors.append("минимум 1 заглавная буква")
        if not re.search(r"\d", v):
            errors.append("минимум 1 цифра")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("минимум 1 спецсимвол")
        if errors:
            raise ValueError(f"Пароль слишком слабый: {', '.join(errors)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str
    device_name: str


class OtpVerifyRequest(BaseModel):
    """
    Используется на двух этапах:
      - После /register  → подтверждение аккаунта
      - После /login     → второй фактор (2FA)
    Клиент передаёт login_session_token полученный из предыдущего ответа.
    Этот токен — НЕ access token. Он короткоживущий (5 мин) и одноразовый.
    """
    login_session_token: str
    otp_code: str


class TokenResponse(BaseModel):
    """Финальные токены. Выдаются ТОЛЬКО после успешного прохождения OTP."""
    access_token: str
    refresh_token: str
    message: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
    device_id: str


class LogoutRequest(BaseModel):
    device_id: str


class MessageResponse(BaseModel):
    message: str
    # Временный токен для шага MFA. Не путать с access/refresh токеном.
    login_session_token: str | None = None