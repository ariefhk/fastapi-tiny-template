from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.webhook_event_model import WebhookEventModel


class WebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        provider: str,
        external_event_id: str,
        type: str,
        payload: Optional[dict] = None,
        processed_at: Optional[datetime] = None,
    ) -> WebhookEventModel:
        event = WebhookEventModel(
            provider=provider,
            external_event_id=external_event_id,
            type=type,
            payload=payload,
            processed_at=processed_at,
        )
        self._session.add(event)
        return event
