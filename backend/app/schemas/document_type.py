import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentTypeCreate(BaseModel):
    name: str
    slug: str | None = None
    color: str = "#6366f1"
    icon: str | None = None


class DocumentTypeUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    color: str | None = None
    icon: str | None = None


class DocumentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    color: str
    icon: str | None
    created_at: datetime
    updated_at: datetime
