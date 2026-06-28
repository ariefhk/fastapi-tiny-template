import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class SessionModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable: a freshly registered user may have no company yet.
    active_company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
