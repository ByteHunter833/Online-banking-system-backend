from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class CommunicationService:
    async def send_email(self, to_email: str, subject: str, body: str) -> None:
        if not settings.mail_enabled:
            logger.info("Mock email sent to=%s subject=%s body=%s", to_email, subject, body)
            return

        await asyncio.to_thread(self._send_email_sync, to_email, subject, body)

    def _send_email_sync(self, to_email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
        message["To"] = to_email
        message.set_content(body)

        smtp_class = smtplib.SMTP_SSL if settings.mail_use_tls else smtplib.SMTP
        with smtp_class(settings.mail_host, settings.mail_port, timeout=15) as server:
            server.ehlo()
            if settings.mail_use_starttls and not settings.mail_use_tls:
                server.starttls()
                server.ehlo()
            if settings.mail_username and settings.mail_password:
                server.login(settings.mail_username, settings.mail_password)
            server.send_message(message)

        logger.info("Email sent to=%s subject=%s", to_email, subject)

    async def send_sms(self, to_phone: str, body: str) -> None:
        logger.info("Mock sms sent to=%s body=%s", to_phone, body)
