import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagCreate(BaseModel):
    name: str
    slug: str | None = None
    color: str = "#10b981"


class TagUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    color: str | None = None


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    color: str
    created_at: datetime
    updated_at: datetime
