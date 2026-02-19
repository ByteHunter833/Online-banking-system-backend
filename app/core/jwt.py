from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.db.supabase_db import get_user_by_id

SECRET_KEY = "SUPER_SECRET_CHANGE_LATER"
ALGORITHM = "HS256"
security = HTTPBearer()


##Access token 
def create_access_token(user_id: str):
    payload = {
        "sub": user_id,
        'token_type': 'access',
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

## Refresh token
def create_refresh_token(user_id:str):
    payload = {
        "sub": user_id,
        'token_type': 'refresh',
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


## get current user from access token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # ПРОВЕРКА: это должен быть именно access токен
        if payload.get("token_type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user



## validate refresh token
def validate_refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # ПРОВЕРКА: это должен быть именно refresh токен
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Use refresh token here")
            
        return payload.get("sub") # Возвращаем только ID пользователя
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
