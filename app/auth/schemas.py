from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str | None = None

class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class MessageResponse(BaseModel):
    message: str
