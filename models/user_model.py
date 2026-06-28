import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from databases.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from models.auth_identity_model import AuthIdentityModel
    from models.company_model import CompanyModel
    from models.membership_model import MembershipModel


class UserModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_last_active_company_id", "last_active_company_id"),
    )

    email: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    last_active_company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey(
            "companies.id",
            use_alter=True,
            name="fk_users_last_company",
            ondelete="SET NULL",
        )
    )

    last_active_company: Mapped[Optional["CompanyModel"]] = relationship(
        foreign_keys="[UserModel.last_active_company_id]"
    )
    owned_companies: Mapped[list["CompanyModel"]] = relationship(
        back_populates="owner",
        foreign_keys="[CompanyModel.owner_user_id]",
    )
    memberships: Mapped[list["MembershipModel"]] = relationship(back_populates="user")
    auth_identities: Mapped[list["AuthIdentityModel"]] = relationship(
        back_populates="user"
    )
