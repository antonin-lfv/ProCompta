from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationTypeEnum(str, enum.Enum):
    incomplete_document = "incomplete_document"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    type: Mapped[NotificationTypeEnum] = mapped_column(
        SAEnum(NotificationTypeEnum, name="notificationtypeenum"),
        nullable=False,
        default=NotificationTypeEnum.incomplete_document,
        server_default="incomplete_document",
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
