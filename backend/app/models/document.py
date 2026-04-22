from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Table, Text, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.correspondent import Correspondent
    from app.models.document_type import DocumentType
    from app.models.tag import Tag


document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(nullable=False)
    file_path: Mapped[str] = mapped_column(nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    document_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    amount_ht: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, default=Decimal("0.00"))
    amount_ttc: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    correspondent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("correspondents.id", ondelete="SET NULL"), nullable=True
    )
    document_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True
    )

    correspondent: Mapped[Correspondent | None] = relationship(back_populates="documents")
    document_type: Mapped[DocumentType | None] = relationship(back_populates="documents")
    tags: Mapped[list[Tag]] = relationship(secondary="document_tags", back_populates="documents")
