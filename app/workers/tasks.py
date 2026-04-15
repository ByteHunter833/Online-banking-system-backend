from __future__ import annotations

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notifications.send_email")
def send_email_notification(recipient: str, subject: str, message: str) -> None:
    from app.core.config import settings
    from app.services.communication import CommunicationService

    communication = CommunicationService()
    if settings.mail_enabled:
        communication._send_email_sync(recipient, subject, message)
    else:
        logger.info("Celery mock email recipient=%s subject=%s", recipient, subject)


@celery_app.task(name="notifications.send_sms")
def send_sms_notification(recipient: str, message: str) -> None:
    logger.info("Celery mock sms recipient=%s message=%s", recipient, message)


@celery_app.task(name="statements.generate_export")
def generate_statement_export(export_id: str) -> None:
    from app.services.statement import generate_statement_export_for_id

    asyncio.run(generate_statement_export_for_id(export_id))
