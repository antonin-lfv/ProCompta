from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import Document


class CorrespondentTypeEnum(str, enum.Enum):
    client = "client"
    fournisseur = "fournisseur"
    les_deux = "les_deux"


class Correspondent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "correspondents"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[CorrespondentTypeEnum | None] = mapped_column(
        SAEnum(CorrespondentTypeEnum, name="correspondenttype"),
        nullable=True,
    )

    documents: Mapped[list[Document]] = relationship(back_populates="correspondent")
