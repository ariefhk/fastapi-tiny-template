import enum

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class PlanIntervalEnum(str, enum.Enum):
    MONTH = "month"
    YEAR = "year"


class PlanModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    interval: Mapped[str] = mapped_column(
        String(10), nullable=False, default=PlanIntervalEnum.MONTH.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
