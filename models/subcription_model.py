import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class SubscriptionStatusEnum(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class PaymentProviderEnum(str, enum.Enum):
    STRIPE = "stripe"
    MIDTRANS = "midtrans"
    DOKU = "doku"


class SubscriptionModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_subscription_company"),
        CheckConstraint(
            "status in ('trialing','active','past_due','canceled')",
            name="ck_subscription_status",
        ),
        CheckConstraint(
            "provider in ('stripe','midtrans','doku')", name="ck_subscription_provider"
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SubscriptionStatusEnum.TRIALING.value
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    external_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    external_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(nullable=True)
