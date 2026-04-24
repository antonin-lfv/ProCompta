import subprocess
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import extract, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models.document import CategoryEnum, Document, document_tags
from app.models.tag import Tag
from pydantic import BaseModel

from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate


class ConvertRequest(BaseModel):
    currency: str
    amount: Decimal
from app.services.file_service import ALLOWED_MIME_TYPES, delete_file, save_uploaded_file
from app.services.preview_service import delete_preview, generate_preview

router = APIRouter(prefix="/documents", tags=["documents"])


def _extract_pdf_date(file_path: str) -> date | None:
    try:
        result = subprocess.run(
            ["pdfinfo", "-isodates", file_path],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.startswith(("CreationDate:", "ModDate:")):
                val = line.split(":", 1)[1].strip()
                return datetime.fromisoformat(val).date()
    except Exception:
        pass
    return None

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


@router.get("/upload")
async def upload_get_not_allowed() -> None:
    raise HTTPException(status_code=405, detail="Use POST /upload to upload a file")


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Document:
    mime = file.content_type or ""
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Seuls les PDF et images (JPG, PNG) sont acceptés")

    document_id = uuid.uuid4()
    file_path, file_hash, file_size = await save_uploaded_file(file, document_id)

    duplicate = await session.scalar(select(Document).where(Document.file_hash == file_hash))
    if duplicate:
        delete_file(file_path)
        raise HTTPException(status_code=409, detail="This file already exists", headers={"X-Duplicate-Id": str(duplicate.id)})

    full_path = str(Path(settings.storage_path) / file_path)
    pdf_date = _extract_pdf_date(full_path) if mime == "application/pdf" else None

    try:
        await generate_preview(full_path, document_id, mime)
    except Exception:
        pass

    stem = Path(file.filename or "document").stem
    doc = Document(
        id=document_id,
        title=stem,
        file_path=file_path,
        file_hash=file_hash,
        mime_type=mime,
        file_size=file_size,
        document_date=pdf_date or date.today(),
    )
    session.add(doc)
    await session.commit()
    return await _get_doc_or_404(session, document_id)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    year: int | None = None,
    category: CategoryEnum | None = None,
    correspondent_id: uuid.UUID | None = None,
    document_type_id: uuid.UUID | None = None,
    tag_ids: list[uuid.UUID] = Query(default=[]),
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Document]:
    stmt = select(Document).options(*_with_relations)

    if year:
        stmt = stmt.where(extract("year", Document.document_date) == year)
    if category:
        stmt = stmt.where(Document.category == category)
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


@router.get("/{id}/file")
async def get_document_file(id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    from fastapi.responses import FileResponse
    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(settings.storage_path) / doc.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(
        path,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@router.post("/{id}/convert-currency")
async def convert_currency(
    id: uuid.UUID,
    body: ConvertRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if body.currency == "EUR":
        return {"amount_eur": str(body.amount)}

    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    today = date.today()
    rate_date = min(doc.payment_date or doc.document_date, today)

    async def _ecb_rate(start: str, end: str) -> Decimal | None:
        url = (
            f"https://data-api.ecb.europa.eu/service/data/"
            f"EXR/D.{body.currency}.EUR.SP00.A"
            f"?startPeriod={start}&endPeriod={end}&format=jsondata"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            obs = resp.json()["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
            if not obs:
                return None
            return Decimal(str(obs[str(max(int(k) for k in obs))][0]))

    try:
        rate = await _ecb_rate(
            (rate_date - timedelta(days=10)).isoformat(),
            rate_date.isoformat(),
        ) or await _ecb_rate(
            (today - timedelta(days=30)).isoformat(),
            today.isoformat(),
        )
        if rate is None:
            raise ValueError("No ECB rate available")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Currency conversion failed: {e}")

    return {"amount_eur": str((body.amount / rate).quantize(Decimal("0.01")))}


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
