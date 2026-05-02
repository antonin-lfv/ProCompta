from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class GmailSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "gmail_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sender_email: Mapped[str] = mapped_column(String(500), nullable=False)
    subject_contains: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_name_contains: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correspondent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("correspondents.id", ondelete="SET NULL"), nullable=True
    )
    document_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
