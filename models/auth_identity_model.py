import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from databases.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from models.user_model import UserModel


class AuthProviderEnum(str, enum.Enum):
    PASSWORD = "password"
    GOOGLE = "google"
    GITHUB = "github"
    APPLE = "apple"
    MICROSOFT = "microsoft"


class AuthIdentityModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_identity_provider_uid"
        ),
        UniqueConstraint("user_id", "provider", name="uq_identity_user_provider"),
        Index("ix_auth_identities_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[AuthProviderEnum] = mapped_column(
        Enum(AuthProviderEnum, name="auth_provider")
    )
    provider_user_id: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))

    user: Mapped["UserModel"] = relationship(back_populates="auth_identities")
