from typing import Dict
from uuid import uuid4

users: Dict[str, dict] = {}
otps: Dict[str, str] = {}

def create_user(email: str, password_hash: str):
    user_id = str(uuid4())
    users[user_id] = {
        "id": user_id,
        "email": email,
        "password_hash": password_hash,
        "is_verified": False,
        "device_id": None
    }
    return users[user_id]

def get_user_by_email(email: str):
    return next((u for u in users.values() if u["email"] == email), None)

def save_device_id(user_id: str, device_id: str):
    users[user_id]["device_id"] = device_id
