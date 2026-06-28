from datetime import datetime
from typing import Optional

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class WebhookEventModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_event_id", name="uq_webhook_provider_event"
        ),
    )

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
