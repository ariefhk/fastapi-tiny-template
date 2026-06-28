import datetime as dt
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now_col(*, onupdate: bool = False) -> Mapped[dt.datetime]:
    """Server-side UTC timestamp, set on INSERT. Pass onupdate=True for updated_at columns."""

    onupdate_action = None

    if onupdate:
        onupdate_action = func.now()
    else:
        onupdate_action = None

    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=onupdate_action,
    )


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base with typed columns."""


class TimestampMixin:
    created_at: Mapped[datetime] = utc_now_col()
    updated_at: Mapped[datetime] = utc_now_col(onupdate=True)


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class SoftDeleteMixin:
    """Marks a model as soft-deletable.

    `deleted_at IS NULL` means the row is live. Setting it to a timestamp
    means the row has been logically removed but is still on disk.

    Tables using this mixin require, by convention:
      * Every read query filters `WHERE deleted_at IS NULL`.
      * The service's `delete` method sets `deleted_at` instead of
        issuing a SQL DELETE.
      * Any `task_items` (or similar polymorphic refs) pointing at the
        row stay valid for read-side display; cleanup of long-dead
        references is a separate sweep job's responsibility.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
