import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from databases.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from models.company_model import CompanyModel
    from models.user_model import UserModel


class MembershipStatusEnum(str, enum.Enum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MembershipModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_membership_user_company"),
        Index("ix_memberships_user_id", "user_id"),
        Index("ix_memberships_company_id", "company_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    status: Mapped[MembershipStatusEnum] = mapped_column(
        Enum(MembershipStatusEnum, name="membership_status"),
        default=MembershipStatusEnum.ACTIVE,
    )

    user: Mapped["UserModel"] = relationship(back_populates="memberships")
    company: Mapped["CompanyModel"] = relationship(back_populates="memberships")
