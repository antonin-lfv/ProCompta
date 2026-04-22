from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentType(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_types"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    color: Mapped[str] = mapped_column(nullable=False, default="#6366f1")
    icon: Mapped[str | None] = mapped_column(nullable=True)

    documents: Mapped[list[Document]] = relationship(back_populates="document_type")
