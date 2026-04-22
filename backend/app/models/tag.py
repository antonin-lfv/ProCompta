from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import Document


class Tag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    color: Mapped[str] = mapped_column(nullable=False, default="#10b981")

    documents: Mapped[list[Document]] = relationship(
        secondary="document_tags", back_populates="tags"
    )
