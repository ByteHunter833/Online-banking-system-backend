from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class WebhookService:
    async def publish_event(self, event_name: str, payload: dict) -> None:
        logger.info("Webhook placeholder published event=%s payload=%s", event_name, payload)

