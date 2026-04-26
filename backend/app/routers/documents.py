import subprocess
import tempfile
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import extract, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models.document import CategoryEnum, Document, document_tags
from app.models.document_activity import ActivityEventEnum, DocumentActivity
from app.models.notification import Notification, NotificationTypeEnum
from app.models.tag import Tag
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.file_service import ALLOWED_MIME_TYPES, delete_file, hash_bytes, save_file_bytes
from app.services.preview_service import delete_preview, generate_preview


class ConvertRequest(BaseModel):
    currency: str
    amount: Decimal


class GenericConvertRequest(BaseModel):
    currency: str
    amount: Decimal
    date: str | None = None  # ISO date, optionnel — défaut: aujourd'hui


async def _fetch_ecb_rate(currency: str, rate_date: date) -> Decimal | None:
    today = date.today()

    async def _call(start: str, end: str) -> Decimal | None:
        url = (
            f"https://data-api.ecb.europa.eu/service/data/"
            f"EXR/D.{currency}.EUR.SP00.A"
            f"?startPeriod={start}&endPeriod={end}&format=jsondata"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            obs = resp.json()["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
            if not obs:
                return None
            return Decimal(str(obs[str(max(int(k) for k in obs))][0]))

    return await _call(
        (rate_date - timedelta(days=10)).isoformat(),
        rate_date.isoformat(),
    ) or await _call(
        (today - timedelta(days=30)).isoformat(),
        today.isoformat(),
    )

router = APIRouter(prefix="/documents", tags=["documents"])


def _is_complete(doc: Document) -> bool:
    return bool(
        doc.document_type_id
        and doc.correspondent_id
        and (doc.category == CategoryEnum.autre or doc.amount_ttc)
    )


def _missing_body(doc: Document) -> str:
    missing = []
    if not doc.correspondent_id:
        missing.append("correspondant")
    if not doc.document_type_id:
        missing.append("type")
    if doc.category != CategoryEnum.autre and not doc.amount_ttc:
        missing.append("montant")
    return "Sans " + " · sans ".join(missing) if missing else "Informations incomplètes"


async def _sync_notification(doc: Document, session: AsyncSession) -> None:
    unread_result = await session.execute(
        select(Notification).where(Notification.document_id == doc.id, Notification.read == False)
    )
    unread = list(unread_result.scalars().all())

    if _is_complete(doc):
        for n in unread:
            n.read = True
    else:
        if not unread:
            existing = await session.scalar(
                select(Notification)
                .where(Notification.document_id == doc.id)
                .order_by(Notification.created_at.desc())
                .limit(1)
            )
            if existing:
                existing.read = False
                existing.title = f"« {doc.title} » - informations manquantes"
                existing.body = _missing_body(doc)
            else:
                session.add(Notification(
                    type=NotificationTypeEnum.incomplete_document,
                    document_id=doc.id,
                    title=f"« {doc.title} » - informations manquantes",
                    body=_missing_body(doc),
                ))
    await session.commit()


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

    content = await file.read()
    file_hash = hash_bytes(content)
    file_size = len(content)

    duplicate = await session.scalar(select(Document).where(Document.file_hash == file_hash))
    if duplicate:
        raise HTTPException(status_code=409, detail="This file already exists", headers={"X-Duplicate-Id": str(duplicate.id)})

    stem = Path(file.filename or "document").stem
    document_id = uuid.uuid4()

    pdf_date = None
    if mime == "application/pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        pdf_date = _extract_pdf_date(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

    doc_date = pdf_date or date.today()
    file_path = await save_file_bytes(content, document_id, doc_date, stem, mime)
    full_path = str(Path(settings.storage_path) / file_path)

    try:
        await generate_preview(full_path, document_id, mime)
    except Exception:
        pass

    doc = Document(
        id=document_id,
        title=stem,
        file_path=file_path,
        file_hash=file_hash,
        mime_type=mime,
        file_size=file_size,
        document_date=doc_date,
    )
    session.add(doc)
    await session.commit()

    session.add(Notification(
        type=NotificationTypeEnum.incomplete_document,
        document_id=document_id,
        title=f"« {stem} » importé - à compléter",
        body="Sans correspondant · Sans type",
    ))
    session.add(DocumentActivity(
        document_id=document_id,
        event_type=ActivityEventEnum.uploaded,
    ))
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
    old_archived = doc.archived

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

    if "archived" in update_data and doc.archived != old_archived:
        session.add(DocumentActivity(
            document_id=id,
            event_type=ActivityEventEnum.archived if doc.archived else ActivityEventEnum.unarchived,
        ))
        await session.commit()

    await _sync_notification(doc, session)
    return await _get_doc_or_404(session, id)


@router.get("/{id}/file")
async def get_document_file(id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)):
    from fastapi.responses import FileResponse, Response
    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(settings.storage_path) / doc.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    etag = f'"{doc.file_hash}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return FileResponse(
        path,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{path.name}"',
            "ETag": etag,
            "Cache-Control": "private, max-age=31536000, immutable",
        },
    )


@router.post("/convert-currency")
async def convert_currency_generic(body: GenericConvertRequest) -> dict:
    """Conversion BCE sans document — utilisé par l'import batch."""
    if body.currency == "EUR":
        return {"amount_eur": str(body.amount)}
    today = date.today()
    rate_date = today
    if body.date:
        try:
            rate_date = min(date.fromisoformat(body.date), today)
        except ValueError:
            pass
    try:
        rate = await _fetch_ecb_rate(body.currency, rate_date)
        if rate is None:
            raise ValueError("No ECB rate available")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Currency conversion failed: {e}")
    return {"amount_eur": str((body.amount / rate).quantize(Decimal("0.01")))}


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
    try:
        rate = await _fetch_ecb_rate(body.currency, rate_date)
        if rate is None:
            raise ValueError("No ECB rate available")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Currency conversion failed: {e}")

    return {"amount_eur": str((body.amount / rate).quantize(Decimal("0.01")))}


@router.get("/{id}/activity")
async def get_document_activity(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        select(DocumentActivity)
        .where(DocumentActivity.document_id == id)
        .order_by(DocumentActivity.created_at.asc())
    )
    return [
        {
            "id": str(a.id),
            "event_type": a.event_type.value,
            "old_value": a.old_value,
            "new_value": a.new_value,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


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
