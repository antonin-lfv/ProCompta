import asyncio
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.document import CategoryEnum, Document
from app.models.gmail_import_log import GmailImportLog
from app.models.gmail_source import GmailSource
from app.models.tag import Tag
from app.services.file_service import hash_bytes, save_file_bytes

router = APIRouter(tags=["gmail"])


class GmailSourceCreate(BaseModel):
    name: str
    sender_email: str
    subject_contains: str | None = None
    attachment_name_contains: str | None = None
    correspondent_id: uuid.UUID | None = None
    document_type_id: uuid.UUID | None = None
    active: bool = True


class GmailSourceUpdate(BaseModel):
    name: str | None = None
    sender_email: str | None = None
    subject_contains: str | None = None
    attachment_name_contains: str | None = None
    correspondent_id: uuid.UUID | None = None
    document_type_id: uuid.UUID | None = None
    active: bool | None = None


class GmailSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    sender_email: str
    subject_contains: str | None
    attachment_name_contains: str | None
    correspondent_id: uuid.UUID | None
    document_type_id: uuid.UUID | None
    active: bool
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/gmail/account")
async def get_gmail_account():
    from app.services.gmail_service import check_connection
    ok, result = await asyncio.to_thread(check_connection)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"email": result}


@router.get("/gmail/sources", response_model=list[GmailSourceResponse])
async def list_sources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(GmailSource).order_by(GmailSource.name))
    return result.scalars().all()


@router.post("/gmail/sources", response_model=GmailSourceResponse, status_code=201)
async def create_source(body: GmailSourceCreate, session: AsyncSession = Depends(get_session)):
    source = GmailSource(**body.model_dump())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


@router.patch("/gmail/sources/{source_id}", response_model=GmailSourceResponse)
async def update_source(
    source_id: uuid.UUID,
    body: GmailSourceUpdate,
    session: AsyncSession = Depends(get_session),
):
    source = await session.get(GmailSource, source_id)
    if not source:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    await session.commit()
    await session.refresh(source)
    return source


@router.delete("/gmail/sources/{source_id}", status_code=204)
async def delete_source(source_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    source = await session.get(GmailSource, source_id)
    if not source:
        raise HTTPException(status_code=404)
    await session.delete(source)
    await session.commit()


@router.post("/gmail/sources/{source_id}/sync")
async def sync_source(
    source_id: uuid.UUID,
    after_date: date | None = Query(None),
    before_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.gmail_configured:
        raise HTTPException(status_code=400, detail="Gmail OAuth non configuré dans .env")

    source = await session.get(GmailSource, source_id)
    if not source:
        raise HTTPException(status_code=404)

    imported, skipped, errors = await _run_sync(source, session, after_date, before_date)
    source.last_synced_at = datetime.now(timezone.utc)
    await session.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors, "source": source.name}


@router.post("/gmail/sync")
async def sync_all(
    after_date: date | None = Query(None),
    before_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.gmail_configured:
        raise HTTPException(status_code=400, detail="Gmail OAuth non configuré dans .env")

    result = await session.execute(select(GmailSource).where(GmailSource.active == True))
    sources = result.scalars().all()

    total_imported = total_skipped = total_errors = 0
    for source in sources:
        imp, skp, err = await _run_sync(source, session, after_date, before_date)
        total_imported += imp
        total_skipped += skp
        total_errors += err
        source.last_synced_at = datetime.now(timezone.utc)

    await session.commit()
    return {"imported": total_imported, "skipped": total_skipped, "errors": total_errors}


async def _get_or_create_gmail_tag(session: AsyncSession) -> Tag:
    tag = await session.scalar(select(Tag).where(Tag.slug == "auto"))
    if not tag:
        tag = Tag(name="Auto", slug="auto", color="#6366f1")
        session.add(tag)
        await session.flush()
    return tag


async def _run_sync(
    source: GmailSource,
    session: AsyncSession,
    after_date: date | None = None,
    before_date: date | None = None,
) -> tuple[int, int, int]:
    from app.services.gmail_service import fetch_invoices

    already_result = await session.execute(
        select(GmailImportLog.gmail_message_id).where(
            GmailImportLog.source_id == source.id,
            GmailImportLog.status == "imported",
        )
    )
    already_imported: set[str] = set(already_result.scalars().all())

    try:
        attachments = await asyncio.to_thread(
            fetch_invoices,
            source.sender_email,
            source.subject_contains,
            source.attachment_name_contains,
            already_imported,
            after_date,
            before_date,
        )
    except Exception as exc:
        return 0, 0, 1

    gmail_tag = await _get_or_create_gmail_tag(session)

    imported = skipped = errors = 0

    for att in attachments:
        msg_id = att["message_id"]
        file_hash = hash_bytes(att["data"])

        exists = await session.scalar(select(Document.id).where(Document.file_hash == file_hash))
        if exists:
            log = GmailImportLog(
                gmail_message_id=msg_id,
                source_id=source.id,
                document_id=exists,
                status="skipped",
                error_msg="Fichier déjà importé (doublon hash)",
            )
            session.add(log)
            skipped += 1
            continue

        doc_id = uuid.uuid4()
        email_date = att["date"].date() if hasattr(att["date"], "date") else att["date"]
        title = f"Invoice-{source.name}-{str(doc_id)[:8]}"

        try:
            file_path = await save_file_bytes(
                att["data"], doc_id, email_date, title, "application/pdf"
            )
        except Exception as exc:
            log = GmailImportLog(
                gmail_message_id=msg_id,
                source_id=source.id,
                status="error",
                error_msg=str(exc)[:500],
            )
            session.add(log)
            errors += 1
            continue

        doc = Document(
            id=doc_id,
            title=title,
            file_path=file_path,
            file_hash=file_hash,
            mime_type="application/pdf",
            file_size=len(att["data"]),
            document_date=email_date,
            category=CategoryEnum.depense,
            correspondent_id=source.correspondent_id,
            document_type_id=source.document_type_id,
            currency="EUR",
            tags=[gmail_tag],
        )
        session.add(doc)
        await session.flush()  # doc + document_tags doivent exister avant le log

        log = GmailImportLog(
            gmail_message_id=msg_id,
            source_id=source.id,
            document_id=doc_id,
            status="imported",
        )
        session.add(log)
        await session.flush()
        imported += 1

    return imported, skipped, errors
