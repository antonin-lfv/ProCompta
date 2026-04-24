import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.document import CategoryEnum
from app.schemas.correspondent import CorrespondentResponse
from app.schemas.document_type import DocumentTypeResponse
from app.schemas.tag import TagResponse


class DocumentCreate(BaseModel):
    title: str
    category: CategoryEnum = CategoryEnum.autre
    document_date: date
    payment_date: date | None = None
    amount_ht: Decimal | None = None
    vat_amount: Decimal | None = None
    vat_rate: Decimal = Decimal("0.00")
    amount_ttc: Decimal | None = None
    amount_ttc_eur: Decimal | None = None
    currency: str = "EUR"
    notes: str | None = None
    correspondent_id: uuid.UUID | None = None
    document_type_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] = []


class DocumentUpdate(BaseModel):
    title: str | None = None
    category: CategoryEnum | None = None
    document_date: date | None = None
    payment_date: date | None = None
    amount_ht: Decimal | None = None
    vat_amount: Decimal | None = None
    vat_rate: Decimal | None = None
    amount_ttc: Decimal | None = None
    amount_ttc_eur: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    correspondent_id: uuid.UUID | None = None
    document_type_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: CategoryEnum
    file_path: str
    file_hash: str
    mime_type: str
    file_size: int
    document_date: date
    payment_date: date | None
    amount_ht: Decimal | None
    vat_amount: Decimal | None
    vat_rate: Decimal | None
    amount_ttc: Decimal | None
    amount_ttc_eur: Decimal | None
    currency: str
    notes: str | None
    correspondent_id: uuid.UUID | None
    document_type_id: uuid.UUID | None
    correspondent: CorrespondentResponse | None
    document_type: DocumentTypeResponse | None
    tags: list[TagResponse]
    created_at: datetime
    updated_at: datetime
