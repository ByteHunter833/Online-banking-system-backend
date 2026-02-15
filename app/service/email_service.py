from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_code(email_to: str, code: str):
    message = MessageSchema(
        subject="Ваш код подтверждения",
        recipients=[email_to],
        body=f"Ваш код для входа: {code}. Он действует 5 минут.",
        subtype=MessageType.plain
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)