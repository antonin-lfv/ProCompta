import asyncio
import base64
import hashlib
import secrets
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.document import CategoryEnum, Document
from app.models.gmail_import_log import GmailImportLog
from app.models.gmail_source import GmailSource
from app.models.tag import Tag
from app.models.user import User
from app.services.file_service import hash_bytes, save_file_bytes
from app.services.gmail_service import (
    GMAIL_SCOPES,
    check_connection,
    fetch_invoices,
    resolve_credentials,
)

router = APIRouter(tags=["gmail"])

_REDIRECT_URI_PATH = "/api/gmail/oauth/callback"


# ── Schémas ───────────────────────────────────────────────────────────────────

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


class GmailCredentialsBody(BaseModel):
    client_id: str
    client_secret: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _redirect_uri(request) -> str:
    return f"http://localhost:{settings.api_port}{_REDIRECT_URI_PATH}"


async def _get_user(session: AsyncSession) -> User | None:
    return await session.scalar(select(User))


# ── OAuth setup ───────────────────────────────────────────────────────────────

@router.post("/gmail/credentials")
async def save_credentials(
    body: GmailCredentialsBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, request.state.user.id)
    user.gmail_client_id = body.client_id.strip()
    user.gmail_client_secret = body.client_secret.strip()
    user.gmail_refresh_token = None
    user.gmail_oauth_state = None
    await session.commit()
    return {"ok": True}


@router.get("/gmail/oauth/start")
async def oauth_start(request: Request, session: AsyncSession = Depends(get_session)):
    from google_auth_oauthlib.flow import Flow

    user = await session.get(User, request.state.user.id)
    if not user or not user.gmail_client_id or not user.gmail_client_secret:
        raise HTTPException(status_code=400, detail="Renseignez d'abord le Client ID et Client Secret")

    redirect_uri = _redirect_uri(request)
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": user.gmail_client_id,
                "client_secret": user.gmail_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri,
    )

    # PKCE - génère un code_verifier et son code_challenge S256
    code_verifier = secrets.token_urlsafe(96)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    user.gmail_oauth_state = state
    user.gmail_code_verifier = code_verifier
    await session.commit()
    return RedirectResponse(auth_url)


@router.get("/gmail/oauth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(default=None),
    state: str = Query(default=None),
    error: str = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    from google_auth_oauthlib.flow import Flow

    if error:
        return RedirectResponse(f"/automations?oauth_error={error}")

    if not code or not state:
        return RedirectResponse("/automations?oauth_error=missing_params")

    user = await session.scalar(select(User).where(User.gmail_oauth_state == state))
    if not user:
        return RedirectResponse("/automations?oauth_error=invalid_state")

    redirect_uri = _redirect_uri(request)
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": user.gmail_client_id,
                "client_secret": user.gmail_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri,
    )
    try:
        await asyncio.to_thread(
            flow.fetch_token, code=code, code_verifier=user.gmail_code_verifier
        )
    except Exception as exc:
        return RedirectResponse(f"/automations?oauth_error={str(exc)[:100]}")

    creds = flow.credentials
    if not creds.refresh_token:
        return RedirectResponse("/automations?oauth_error=no_refresh_token")

    user.gmail_refresh_token = creds.refresh_token
    user.gmail_oauth_state = None
    await session.commit()
    return RedirectResponse("/automations?oauth_success=1")


@router.delete("/gmail/credentials")
async def delete_credentials(request: Request, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, request.state.user.id)
    user.gmail_client_id = None
    user.gmail_client_secret = None
    user.gmail_refresh_token = None
    user.gmail_oauth_state = None
    await session.commit()
    return {"ok": True}


# ── Account check ─────────────────────────────────────────────────────────────

@router.get("/gmail/account")
async def get_gmail_account(request: Request, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, request.state.user.id)
    creds = resolve_credentials(user)
    if not creds:
        raise HTTPException(status_code=400, detail="Gmail non configuré")
    ok, result = await asyncio.to_thread(check_connection, *creds)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"email": result}


# ── Sources CRUD ──────────────────────────────────────────────────────────────

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


# ── Sync ──────────────────────────────────────────────────────────────────────

@router.post("/gmail/sources/{source_id}/sync")
async def sync_source(
    source_id: uuid.UUID,
    request: Request,
    after_date: date | None = Query(None),
    before_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, request.state.user.id)
    creds = resolve_credentials(user)
    if not creds:
        raise HTTPException(status_code=400, detail="Gmail OAuth non configuré")

    source = await session.get(GmailSource, source_id)
    if not source:
        raise HTTPException(status_code=404)

    imported, skipped, errors = await _run_sync(source, session, creds, after_date, before_date)
    source.last_synced_at = datetime.now(timezone.utc)
    await session.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors, "source": source.name}


@router.post("/gmail/sync")
async def sync_all(
    request: Request,
    after_date: date | None = Query(None),
    before_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, request.state.user.id)
    creds = resolve_credentials(user)
    if not creds:
        raise HTTPException(status_code=400, detail="Gmail OAuth non configuré")

    result = await session.execute(select(GmailSource).where(GmailSource.active == True))
    sources = result.scalars().all()

    total_imported = total_skipped = total_errors = 0
    for source in sources:
        imp, skp, err = await _run_sync(source, session, creds, after_date, before_date)
        total_imported += imp
        total_skipped += skp
        total_errors += err
        source.last_synced_at = datetime.now(timezone.utc)

    await session.commit()
    return {"imported": total_imported, "skipped": total_skipped, "errors": total_errors}


# ── Internals ─────────────────────────────────────────────────────────────────

async def _get_or_create_auto_tag(session: AsyncSession) -> Tag:
    tag = await session.scalar(select(Tag).where(Tag.slug == "auto"))
    if not tag:
        tag = Tag(name="Auto", slug="auto", color="#6366f1")
        session.add(tag)
        await session.flush()
    return tag


async def _run_sync(
    source: GmailSource,
    session: AsyncSession,
    creds: tuple[str, str, str],
    after_date: date | None = None,
    before_date: date | None = None,
) -> tuple[int, int, int]:
    already_result = await session.execute(
        select(GmailImportLog.gmail_message_id)
        .join(Document, GmailImportLog.document_id == Document.id)
        .where(
            GmailImportLog.source_id == source.id,
            GmailImportLog.status == "imported",
        )
    )
    already_imported: set[str] = set(already_result.scalars().all())

    client_id, client_secret, refresh_token = creds
    try:
        attachments = await asyncio.to_thread(
            fetch_invoices,
            client_id,
            client_secret,
            refresh_token,
            source.sender_email,
            source.subject_contains,
            source.attachment_name_contains,
            already_imported,
            after_date,
            before_date,
        )
    except Exception as exc:
        return 0, 0, 1

    auto_tag = await _get_or_create_auto_tag(session)

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
            tags=[auto_tag],
        )
        session.add(doc)
        await session.flush()

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
