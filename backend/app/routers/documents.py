import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import extract, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models.document import Document, document_tags
from app.models.tag import Tag
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.file_service import ALLOWED_MIME_TYPES, delete_file, save_uploaded_file
from app.services.preview_service import delete_preview, generate_preview

router = APIRouter(prefix="/documents", tags=["documents"])

_with_relations = [
    selectinload(Document.tags),
    selectinload(Document.correspondent),
    selectinload(Document.document_type),
]


async def _get_doc_or_404(session: AsyncSession, id: uuid.UUID) -> Document:
    result = await session.execute(
        select(Document).options(*_with_relations).where(Document.id == id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/years", response_model=list[int])
async def list_years(session: AsyncSession = Depends(get_session)) -> list[int]:
    result = await session.execute(
        select(extract("year", Document.document_date).label("year"))
        .distinct()
        .order_by(extract("year", Document.document_date).desc())
    )
    return [int(row.year) for row in result.all()]


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Document:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    document_id = uuid.uuid4()
    file_path, file_hash, file_size = await save_uploaded_file(file, document_id)

    duplicate = await session.scalar(select(Document).where(Document.file_hash == file_hash))
    if duplicate:
        delete_file(file_path)
        raise HTTPException(status_code=409, detail="This file already exists", headers={"X-Duplicate-Id": str(duplicate.id)})

    try:
        pdf_full_path = str(Path(settings.storage_path) / file_path)
        await generate_preview(pdf_full_path, document_id)
    except Exception:
        pass  # preview failure is non-blocking

    stem = Path(file.filename or "document").stem
    doc = Document(
        id=document_id,
        title=stem,
        file_path=file_path,
        file_hash=file_hash,
        mime_type=file.content_type or "application/pdf",
        file_size=file_size,
        document_date=date.today(),
    )
    session.add(doc)
    await session.commit()
    return await _get_doc_or_404(session, document_id)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    year: int | None = None,
    correspondent_id: uuid.UUID | None = None,
    document_type_id: uuid.UUID | None = None,
    tag_ids: list[uuid.UUID] = Query(default=[]),
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Document]:
    stmt = select(Document).options(*_with_relations)

    if year:
        stmt = stmt.where(extract("year", Document.document_date) == year)
    if correspondent_id:
        stmt = stmt.where(Document.correspondent_id == correspondent_id)
    if document_type_id:
        stmt = stmt.where(Document.document_type_id == document_type_id)
    if search:
        stmt = stmt.where(Document.title.ilike(f"%{search}%"))
    for tag_id in tag_ids:
        stmt = stmt.where(
            Document.id.in_(
                select(document_tags.c.document_id).where(document_tags.c.tag_id == tag_id)
            )
        )

    stmt = stmt.order_by(Document.document_date.desc(), Document.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{id}", response_model=DocumentResponse)
async def get_document(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Document:
    return await _get_doc_or_404(session, id)


@router.patch("/{id}", response_model=DocumentResponse)
async def update_document(
    id: uuid.UUID, data: DocumentUpdate, session: AsyncSession = Depends(get_session)
) -> Document:
    doc = await _get_doc_or_404(session, id)

    update_data = data.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)

    for field, value in update_data.items():
        setattr(doc, field, value)

    if tag_ids is not None:
        if tag_ids:
            tags_result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
            doc.tags = list(tags_result.scalars().all())
        else:
            doc.tags = []

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Invalid correspondent or document type")

    return await _get_doc_or_404(session, id)


@router.delete("/{id}", status_code=204)
async def delete_document(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.file_path
    await session.delete(doc)
    await session.commit()

    delete_file(file_path)
    delete_preview(id)
