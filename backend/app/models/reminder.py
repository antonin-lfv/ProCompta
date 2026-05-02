from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Reminder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reminders"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency_days: Mapped[int] = mapped_column(Integer, nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    notify_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notify_inapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
