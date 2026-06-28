import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from databases.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from models.company_model import CompanyModel
    from models.user_model import UserModel


class ActivityLogAction(str, enum.Enum):
    # CRUD actions
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    # AUTH action
    LOGIN = "login"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    TOKEN_REVOKE = "token_revoke"
    REFRESH = "token_refresh"


class ActivityLogModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_company_created", "company_id", "created_at"),)

    # Foreign Key
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Polymorphic target — plain columns, intentionally no FK.
    action: Mapped[ActivityLogAction] = mapped_column(
        Enum(ActivityLogAction), nullable=False
    )
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)

    # State snapshots — changed fields only.
    before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Request context for forensics.
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relations
    company: Mapped[Optional["CompanyModel"]] = relationship(foreign_keys=[company_id])
    actor: Mapped[Optional["UserModel"]] = relationship(foreign_keys=[actor_id])
