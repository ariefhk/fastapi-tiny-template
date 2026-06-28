import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from databases.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from models.membership_model import MembershipModel
    from models.subscription_model import SubscriptionModel
    from models.user_model import UserModel


class CompanyModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_slug", "slug", unique=True),
        Index("ix_companies_owner_user_id", "owner_user_id"),
    )

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_companies_owner"), nullable=True
    )

    owner: Mapped[Optional["UserModel"]] = relationship(
        back_populates="owned_companies",
        foreign_keys="[CompanyModel.owner_user_id]",
    )
    memberships: Mapped[list["MembershipModel"]] = relationship(back_populates="company")
    subscription: Mapped[Optional["SubscriptionModel"]] = relationship(
        back_populates="company", uselist=False
    )
