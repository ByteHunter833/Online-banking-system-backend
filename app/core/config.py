from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    # Меняем имя, чтобы соответствовало .env
    SUPABASE_SERVICE_ROLE_KEY: str 
    
    # Email
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    SECRET_KEY: str
    model_config = SettingsConfigDict(
        env_file="app/.env", # Убедись, что .env действительно лежит в app/
        env_file_encoding="utf-8",
        extra="ignore" # Игнорировать лишние переменные
    )

settings = Settings(
    
)