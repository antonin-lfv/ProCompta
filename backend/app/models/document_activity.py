from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ActivityEventEnum(str, enum.Enum):
    uploaded = "uploaded"
    title_changed = "title_changed"
    correspondent_changed = "correspondent_changed"
    type_changed = "type_changed"
    category_changed = "category_changed"
    amount_changed = "amount_changed"
    date_changed = "date_changed"
    notes_changed = "notes_changed"
    archived = "archived"
    unarchived = "unarchived"


class DocumentActivity(Base, UUIDMixin):
    __tablename__ = "document_activity"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[ActivityEventEnum] = mapped_column(
        SAEnum(ActivityEventEnum, name="activityeventenum"), nullable=False
    )
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
