import asyncio
import subprocess
import tempfile
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models.correspondent import Correspondent
from app.models.document import CategoryEnum, Document, document_tags
from app.models.document_activity import ActivityEventEnum, DocumentActivity
from app.models.document_type import DocumentType
from app.models.notification import Notification, NotificationTypeEnum
from app.models.tag import Tag
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.file_service import ALLOWED_MIME_TYPES, delete_file, hash_bytes, save_file_bytes
from app.services.preview_service import delete_preview, generate_preview


class BulkActionRequest(BaseModel):
    ids: list[uuid.UUID]
    archived: bool = True


class ConvertRequest(BaseModel):
    currency: str
    amount: Decimal
    payment_date: str | None = None  # ISO date, prioritaire sur doc.payment_date


class GenericConvertRequest(BaseModel):
    currency: str
    amount: Decimal
    date: str | None = None  # ISO date, optionnel - défaut: aujourd'hui


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


# Synonymes anglais pour les types de document courants
_TYPE_SYNONYMS: dict[str, list[str]] = {
    "facture":              ["invoice", "bill"],
    "devis":                ["quote", "quotation", "estimate"],
    "contrat":              ["contract", "agreement"],
    "bon de commande":      ["purchase order", "order form"],
    "relevé":               ["statement", "account statement"],
    "reçu":                 ["receipt"],
    "bulletin de salaire":  ["payslip", "pay slip", "payroll"],
    "rapport":              ["report"],
    "avenant":              ["amendment", "addendum"],
    "attestation":          ["certificate", "certification"],
    "avoir":                ["credit note", "credit memo"],
    "bordereau":            ["remittance", "slip"],
}


def _extract_pdf_text(file_path: str) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-q", file_path, "-"],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout
    except Exception:
        return ""


def _extract_image_text(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, lang="fra+eng")
    except Exception:
        return ""


def _extract_document_text(file_path: str, mime: str) -> str:
    if mime == "application/pdf":
        return _extract_pdf_text(file_path)
    if mime in ("image/jpeg", "image/png"):
        return _extract_image_text(file_path)
    return ""


async def _auto_detect_fields(text: str, session: AsyncSession) -> dict:
    if not text.strip():
        return {}
    text_lower = text[:8000].lower()
    detected: dict = {}

    # Correspondent - prefer longer names to reduce false positives
    corr_rows = (await session.execute(
        select(Correspondent).order_by(func.length(Correspondent.name).desc())
    )).scalars().all()
    for corr in corr_rows:
        if len(corr.name) >= 3 and corr.name.lower() in text_lower:
            detected["correspondent_id"] = corr.id
            break

    # Document type - check French name then English synonyms
    dt_rows = (await session.execute(
        select(DocumentType).order_by(func.length(DocumentType.name).desc())
    )).scalars().all()
    for dt in dt_rows:
        name_lower = dt.name.lower()
        synonyms = _TYPE_SYNONYMS.get(name_lower, [])
        if name_lower in text_lower or any(s in text_lower for s in synonyms):
            detected["document_type_id"] = dt.id
            break

    return detected


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


@router.post("/detect", status_code=200)
async def detect_fields_preview(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Extract text and detect correspondent/type without creating a document."""
    mime = file.content_type or ""
    if mime not in ALLOWED_MIME_TYPES:
        return {"correspondent_id": None, "document_type_id": None}
    content = await file.read()
    if not content:
        return {"correspondent_id": None, "document_type_id": None}
    _EXT = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=_EXT.get(mime, ""), delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        text = await asyncio.to_thread(_extract_document_text, tmp_path, mime)
        detected = await _auto_detect_fields(text, session) if text.strip() else {}
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
    return {
        "correspondent_id": str(detected["correspondent_id"]) if "correspondent_id" in detected else None,
        "document_type_id": str(detected["document_type_id"]) if "document_type_id" in detected else None,
    }


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

    _MAX_DOC_SIZE = 50 * 1024 * 1024  # 50 Mo
    content = await file.read()
    if len(content) > _MAX_DOC_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50 Mo)")

    if not content:
        raise HTTPException(status_code=400, detail="Le fichier est vide")

    _MAGIC = {
        "application/pdf": b"%PDF",
        "image/jpeg": b"\xff\xd8\xff",
        "image/png": b"\x89PNG",
    }
    magic = _MAGIC.get(mime, b"")
    if not content.startswith(magic):
        raise HTTPException(status_code=400, detail="Le contenu du fichier ne correspond pas à son type déclaré")

    file_hash = hash_bytes(content)
    file_size = len(content)

    duplicate = await session.scalar(select(Document).where(Document.file_hash == file_hash))
    if duplicate:
        raise HTTPException(status_code=409, detail="This file already exists", headers={"X-Duplicate-Id": str(duplicate.id)})

    stem = Path(file.filename or "document").stem
    document_id = uuid.uuid4()

    pdf_date = None
    if mime == "application/pdf":
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            pdf_date = _extract_pdf_date(tmp_path)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    doc_date = pdf_date or date.today()
    file_path = await save_file_bytes(content, document_id, doc_date, stem, mime)
    full_path = str(Path(settings.storage_path) / file_path)

    try:
        await generate_preview(full_path, document_id, mime)
    except Exception:
        pass

    detected: dict = {}
    text = await asyncio.to_thread(_extract_document_text, full_path, mime)
    if text:
        detected = await _auto_detect_fields(text, session)

    doc = Document(
        id=document_id,
        title=stem,
        file_path=file_path,
        file_hash=file_hash,
        mime_type=mime,
        file_size=file_size,
        document_date=doc_date,
        correspondent_id=detected.get("correspondent_id"),
        document_type_id=detected.get("document_type_id"),
    )
    session.add(doc)
    session.add(DocumentActivity(
        document_id=document_id,
        event_type=ActivityEventEnum.uploaded,
    ))
    await session.commit()

    await _sync_notification(doc, session)

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
    """Conversion BCE sans document - utilisé par l'import batch."""
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
    _override = None
    if body.payment_date:
        try:
            _override = date.fromisoformat(body.payment_date)
        except ValueError:
            pass
    rate_date = min(_override or doc.payment_date or doc.document_date, today)
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


@router.post("/bulk-archive", status_code=200)
async def bulk_archive(body: BulkActionRequest, session: AsyncSession = Depends(get_session)) -> dict:
    if not body.ids:
        return {"updated": 0}
    result = await session.execute(
        select(Document).options(*_with_relations).where(Document.id.in_(body.ids))
    )
    docs = list(result.scalars().all())
    for doc in docs:
        if doc.archived != body.archived:
            doc.archived = body.archived
            session.add(DocumentActivity(
                document_id=doc.id,
                event_type=ActivityEventEnum.archived if body.archived else ActivityEventEnum.unarchived,
            ))
    await session.commit()
    for doc in docs:
        await _sync_notification(doc, session)
    return {"updated": len(docs)}


@router.post("/bulk-delete", status_code=200)
async def bulk_delete(body: BulkActionRequest, session: AsyncSession = Depends(get_session)) -> dict:
    if not body.ids:
        return {"deleted": 0}
    result = await session.execute(
        select(Document).where(Document.id.in_(body.ids))
    )
    docs = list(result.scalars().all())
    file_paths = [(doc.file_path, doc.id) for doc in docs]
    for doc in docs:
        await session.delete(doc)
    await session.commit()
    for file_path, doc_id in file_paths:
        delete_file(file_path)
        delete_preview(doc_id)
    return {"deleted": len(docs)}


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
