import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CorrespondentCreate(BaseModel):
    name: str
    slug: str | None = None
    notes: str | None = None


class CorrespondentUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    notes: str | None = None


class CorrespondentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
