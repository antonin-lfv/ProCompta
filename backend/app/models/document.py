from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Table, Text, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CategoryEnum(str, enum.Enum):
    depense = "depense"
    recette = "recette"
    autre = "autre"

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

    category: Mapped[CategoryEnum] = mapped_column(
        SAEnum(CategoryEnum, name="categoryenum"),
        nullable=False,
        default=CategoryEnum.autre,
        server_default="autre",
    )

    title: Mapped[str] = mapped_column(nullable=False)
    is_manual: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    file_path: Mapped[str | None] = mapped_column(nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    amount_ht: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    prorata_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    amount_ttc: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_ttc_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    is_paid: Mapped[bool | None] = mapped_column(nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")

    correspondent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("correspondents.id", ondelete="SET NULL"), nullable=True
    )
    document_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True
    )

    correspondent: Mapped[Correspondent | None] = relationship(back_populates="documents")
    document_type: Mapped[DocumentType | None] = relationship(back_populates="documents")
    tags: Mapped[list[Tag]] = relationship(secondary="document_tags", back_populates="documents")
