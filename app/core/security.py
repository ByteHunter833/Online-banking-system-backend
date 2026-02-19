from passlib.context import CryptContext
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    
    password_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(password_hex)

def verify_password(password: str, hashed: str) -> bool:
    # Здесь тоже меняем на .hexdigest()
    password_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.verify(password_hex, hashed)

