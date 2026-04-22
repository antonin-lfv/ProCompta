import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.document_type import DocumentType
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeResponse, DocumentTypeUpdate
from app.utils import slugify

router = APIRouter(prefix="/document-types", tags=["document-types"])


@router.get("", response_model=list[DocumentTypeResponse])
async def list_document_types(session: AsyncSession = Depends(get_session)) -> list[DocumentType]:
    result = await session.execute(select(DocumentType).order_by(DocumentType.name))
    return list(result.scalars().all())


@router.post("", response_model=DocumentTypeResponse, status_code=201)
async def create_document_type(
    data: DocumentTypeCreate, session: AsyncSession = Depends(get_session)
) -> DocumentType:
    obj = DocumentType(
        name=data.name,
        slug=data.slug or slugify(data.name),
        color=data.color,
        icon=data.icon,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A document type with this name or slug already exists")
    await session.refresh(obj)
    return obj


@router.get("/{id}", response_model=DocumentTypeResponse)
async def get_document_type(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> DocumentType:
    obj = await session.get(DocumentType, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Document type not found")
    return obj


@router.patch("/{id}", response_model=DocumentTypeResponse)
async def update_document_type(
    id: uuid.UUID, data: DocumentTypeUpdate, session: AsyncSession = Depends(get_session)
) -> DocumentType:
    obj = await session.get(DocumentType, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Document type not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A document type with this slug already exists")
    await session.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
async def delete_document_type(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    obj = await session.get(DocumentType, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Document type not found")
    await session.delete(obj)
    await session.commit()
