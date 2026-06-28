import enum
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class OverrideEffectEnum(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class MembershipPermissionOverrideModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "membership_permission_overrides"
    __table_args__ = (
        UniqueConstraint(
            "membership_id", "permission_id", name="uq_override_member_perm"
        ),
        CheckConstraint("effect in ('allow','deny')", name="ck_override_effect"),
    )

    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    effect: Mapped[str] = mapped_column(String(5), nullable=False)
