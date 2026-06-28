from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from databases.base import Base, TimestampMixin, UUIDPkMixin


class PermissionModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
