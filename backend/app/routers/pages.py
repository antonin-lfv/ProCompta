import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.correspondent import Correspondent
from app.models.document import Document, document_tags
from app.models.document_type import DocumentType
from app.models.tag import Tag
from app.services.file_service import delete_file
from app.services.preview_service import delete_preview
from app.templating import templates
from app.utils import slugify

router = APIRouter(tags=["pages"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid(v: str | None) -> uuid.UUID | None:
    if not v or not v.strip():
        return None
    try:
        return uuid.UUID(v)
    except ValueError:
        return None


def _decimal(v: str | None) -> Decimal | None:
    if not v or not v.strip():
        return None
    try:
        return Decimal(v.replace(",", "."))
    except InvalidOperation:
        return None


def _date(v: str | None) -> date | None:
    if not v or not v.strip():
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


async def _doc_or_404(session: AsyncSession, id: uuid.UUID) -> Document:
    result = await session.execute(
        select(Document)
        .options(
            selectinload(Document.tags),
            selectinload(Document.correspondent),
            selectinload(Document.document_type),
        )
        .where(Document.id == id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return doc


async def _correspondents(session: AsyncSession) -> list[Correspondent]:
    r = await session.execute(select(Correspondent).order_by(Correspondent.name))
    return list(r.scalars().all())


async def _doc_types(session: AsyncSession) -> list[DocumentType]:
    r = await session.execute(select(DocumentType).order_by(DocumentType.name))
    return list(r.scalars().all())


async def _tags(session: AsyncSession) -> list[Tag]:
    r = await session.execute(select(Tag).order_by(Tag.name))
    return list(r.scalars().all())


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    today = date.today()

    total, year_count, month_count, no_tags_count, no_correspondent_count = [
        (await session.scalar(q)) or 0
        for q in [
            select(func.count(Document.id)),
            select(func.count(Document.id)).where(extract("year", Document.document_date) == today.year),
            select(func.count(Document.id)).where(
                extract("year", Document.document_date) == today.year,
                extract("month", Document.document_date) == today.month,
            ),
            select(func.count(Document.id)).where(~Document.id.in_(select(document_tags.c.document_id))),
            select(func.count(Document.id)).where(Document.correspondent_id.is_(None)),
        ]
    ]

    recent_result = await session.execute(
        select(Document)
        .options(selectinload(Document.correspondent), selectinload(Document.document_type), selectinload(Document.tags))
        .order_by(Document.created_at.desc())
        .limit(5)
    )

    return templates.TemplateResponse(request, "pages/dashboard.html", {
        "now": today,
        "total_documents": total,
        "year_count": year_count,
        "month_count": month_count,
        "no_tags_count": no_tags_count,
        "no_correspondent_count": no_correspondent_count,
        "recent_documents": list(recent_result.scalars().all()),
    })


# ── Années ────────────────────────────────────────────────────────────────────

@router.get("/years", response_class=HTMLResponse)
async def years_list(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await session.execute(
        select(
            extract("year", Document.document_date).label("year"),
            func.count(Document.id).label("count"),
            func.sum(Document.amount_ttc).label("total_ttc"),
        )
        .group_by(extract("year", Document.document_date))
        .order_by(extract("year", Document.document_date).desc())
    )
    return templates.TemplateResponse(request, "pages/years.html", {"years_data": result.all()})


# ── Vue année ─────────────────────────────────────────────────────────────────

@router.get("/year/{year}", response_class=HTMLResponse)
async def year_view(
    year: int,
    request: Request,
    correspondent_id: str | None = Query(default=None),
    document_type_id: str | None = Query(default=None),
    tag_ids: list[str] = Query(default=[]),
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    exists = await session.scalar(
        select(func.count(Document.id)).where(extract("year", Document.document_date) == year)
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Aucun document pour cette année")

    corr_uuid = _uuid(correspondent_id)
    dtype_uuid = _uuid(document_type_id)
    tag_uuids = [u for s in tag_ids if (u := _uuid(s))]

    stmt = (
        select(Document)
        .options(selectinload(Document.tags), selectinload(Document.correspondent), selectinload(Document.document_type))
        .where(extract("year", Document.document_date) == year)
    )
    if corr_uuid:
        stmt = stmt.where(Document.correspondent_id == corr_uuid)
    if dtype_uuid:
        stmt = stmt.where(Document.document_type_id == dtype_uuid)
    if search and search.strip():
        stmt = stmt.where(Document.title.ilike(f"%{search.strip()}%"))
    for tid in tag_uuids:
        stmt = stmt.where(Document.id.in_(
            select(document_tags.c.document_id).where(document_tags.c.tag_id == tid)
        ))
    stmt = stmt.order_by(Document.document_date.desc())

    docs = list((await session.execute(stmt)).scalars().all())

    return templates.TemplateResponse(request, "pages/year.html", {
        "year": year,
        "documents": docs,
        "correspondents": await _correspondents(session),
        "doc_types": await _doc_types(session),
        "all_tags": await _tags(session),
        "filters": {
            "correspondent_id": str(corr_uuid) if corr_uuid else "",
            "document_type_id": str(dtype_uuid) if dtype_uuid else "",
            "tag_ids": [str(t) for t in tag_uuids],
            "search": search or "",
        },
        "has_filters": any([corr_uuid, dtype_uuid, tag_uuids, search]),
    })


# ── Tous les documents ───────────────────────────────────────────────────────

@router.get("/documents", response_class=HTMLResponse)
async def documents_list(
    request: Request,
    no_tags: bool = Query(default=False),
    no_correspondent: bool = Query(default=False),
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    stmt = (
        select(Document)
        .options(
            selectinload(Document.tags),
            selectinload(Document.correspondent),
            selectinload(Document.document_type),
        )
    )
    if no_tags:
        stmt = stmt.where(~Document.id.in_(select(document_tags.c.document_id)))
    if no_correspondent:
        stmt = stmt.where(Document.correspondent_id.is_(None))
    if search and search.strip():
        stmt = stmt.where(Document.title.ilike(f"%{search.strip()}%"))
    stmt = stmt.order_by(Document.document_date.desc(), Document.created_at.desc())
    docs = list((await session.execute(stmt)).scalars().all())

    return templates.TemplateResponse(request, "pages/documents.html", {
        "documents": docs,
        "no_tags": no_tags,
        "no_correspondent": no_correspondent,
        "search": search or "",
    })


# ── Édition document ──────────────────────────────────────────────────────────

@router.get("/documents/{id}/edit", response_class=HTMLResponse)
async def document_edit(id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    doc = await _doc_or_404(session, id)
    all_tags_list = await _tags(session)
    return templates.TemplateResponse(request, "pages/document_edit.html", {
        "doc": doc,
        "correspondents": await _correspondents(session),
        "doc_types": await _doc_types(session),
        "all_tags": all_tags_list,
        "doc_tags_json": [{"id": str(t.id), "name": t.name, "color": t.color} for t in doc.tags],
        "all_tags_json": [{"id": str(t.id), "name": t.name, "color": t.color} for t in all_tags_list],
    })


@router.post("/documents/{id}/edit")
async def document_update_form(
    id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)
) -> RedirectResponse:
    doc = await _doc_or_404(session, id)
    form = await request.form()

    if title := str(form.get("title", "")).strip():
        doc.title = title
    if doc_date := _date(str(form.get("document_date", ""))):
        doc.document_date = doc_date

    doc.payment_date = _date(str(form.get("payment_date", "")))
    doc.amount_ht = _decimal(str(form.get("amount_ht", "")))
    doc.vat_amount = _decimal(str(form.get("vat_amount", "")))
    doc.vat_rate = _decimal(str(form.get("vat_rate", "")))
    doc.amount_ttc = _decimal(str(form.get("amount_ttc", "")))
    doc.currency = str(form.get("currency", "EUR")).strip() or "EUR"
    doc.notes = str(form.get("notes", "")).strip() or None
    doc.correspondent_id = _uuid(str(form.get("correspondent_id", "")))
    doc.document_type_id = _uuid(str(form.get("document_type_id", "")))

    tag_uuids = [uuid.UUID(t) for t in form.getlist("tag_ids") if t]
    if tag_uuids:
        tags_result = await session.execute(select(Tag).where(Tag.id.in_(tag_uuids)))
        doc.tags = list(tags_result.scalars().all())
    else:
        doc.tags = []

    await session.commit()
    return RedirectResponse(f"/year/{doc.document_date.year}", status_code=303)


@router.post("/documents/{id}/delete")
async def document_delete_form(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> RedirectResponse:
    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(status_code=404)
    year, file_path, doc_id = doc.document_date.year, doc.file_path, doc.id
    await session.delete(doc)
    await session.commit()
    delete_file(file_path)
    delete_preview(doc_id)
    return RedirectResponse(f"/year/{year}", status_code=303)


# ── Configuration ─────────────────────────────────────────────────────────────

@router.get("/config", response_class=HTMLResponse)
async def config(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    return templates.TemplateResponse(request, "pages/config.html", {
        "correspondents": await _correspondents(session),
        "doc_types": await _doc_types(session),
        "tags": await _tags(session),
        "tab": request.query_params.get("tab", "correspondents"),
    })


@router.post("/config/correspondents")
async def config_add_correspondent(request: Request, session: AsyncSession = Depends(get_session)) -> RedirectResponse:
    form = await request.form()
    if name := str(form.get("name", "")).strip():
        session.add(Correspondent(name=name, slug=slugify(name)))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
    return RedirectResponse("/config?tab=correspondents", status_code=303)


@router.post("/config/document-types")
async def config_add_doc_type(request: Request, session: AsyncSession = Depends(get_session)) -> RedirectResponse:
    form = await request.form()
    if name := str(form.get("name", "")).strip():
        color = str(form.get("color", "#6366f1")).strip()
        session.add(DocumentType(name=name, slug=slugify(name), color=color))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
    return RedirectResponse("/config?tab=types", status_code=303)


@router.post("/config/tags")
async def config_add_tag(request: Request, session: AsyncSession = Depends(get_session)) -> RedirectResponse:
    form = await request.form()
    if name := str(form.get("name", "")).strip():
        color = str(form.get("color", "#10b981")).strip()
        session.add(Tag(name=name, slug=slugify(name), color=color))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
    return RedirectResponse("/config?tab=tags", status_code=303)
