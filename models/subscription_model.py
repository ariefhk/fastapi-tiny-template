import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from databases.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from models.company_model import CompanyModel


class SubscriptionModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_company_id", "company_id", unique=True),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))

    company: Mapped["CompanyModel"] = relationship(back_populates="subscription")
