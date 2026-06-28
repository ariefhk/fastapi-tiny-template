import enum

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class FeatureKindEnum(str, enum.Enum):
    BOOLEAN = "boolean"
    METERED = "metered"


class FeatureModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "features"
    __table_args__ = (
        CheckConstraint("kind in ('boolean','metered')", name="ck_feature_kind"),
    )

    key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(10), nullable=False, default=FeatureKindEnum.BOOLEAN.value
    )
