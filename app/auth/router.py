from fastapi import APIRouter, HTTPException
from app.auth.schemas import (
    LoginRequest,
    MessageResponse,
    OtpVerifyRequest,
    RegisterRequest,
    TokenResponse,
)
from app.auth.service import (
    authenticate_user,
    generate_device_id,
    issue_otp_for_user,
    register_user,
    verify_user_otp,
)
from app.core.jwt import create_access_token
from app.db.supabase_db import save_device_id
from app.service.email_service import send_otp_code

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=MessageResponse)
async def register(data: RegisterRequest):
    try:
        user = register_user(data.email, data.password, data.device_id)
        otp_code = issue_otp_for_user(user["id"])
        await send_otp_code(user["email"], otp_code)
        return {"message": "Registered. OTP sent."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=MessageResponse)
async def login(data: LoginRequest):
    user = authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    requested_device_id = data.device_id or user.get("device_id") or generate_device_id()
    if user.get("device_id") != requested_device_id:
        save_device_id(user["id"], requested_device_id)

    otp_code = issue_otp_for_user(user["id"])
    await send_otp_code(user["email"], otp_code)
    return {"message": "OTP sent."}

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(data: OtpVerifyRequest):
    user, error = verify_user_otp(data.email, data.otp_code)
    if error:
        raise HTTPException(status_code=400, detail=error)

    token = create_access_token(user["id"])
    return {"access_token": token}
