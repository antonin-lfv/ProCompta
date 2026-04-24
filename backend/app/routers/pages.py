import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.correspondent import Correspondent
from app.models.document import CategoryEnum, Document, document_tags
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

    no_type_count, no_correspondent_count = [
        (await session.scalar(q)) or 0
        for q in [
            select(func.count(Document.id)).where(Document.document_type_id.is_(None)),
            select(func.count(Document.id)).where(Document.correspondent_id.is_(None)),
        ]
    ]

    _year_filter = extract("year", Document.document_date) == today.year
    total_depenses = (await session.scalar(
        select(func.sum(Document.amount_ttc))
        .where(_year_filter, Document.category == CategoryEnum.depense)
    )) or Decimal("0")
    total_recettes = (await session.scalar(
        select(func.sum(Document.amount_ttc))
        .where(_year_filter, Document.category == CategoryEnum.recette)
    )) or Decimal("0")
    solde = total_recettes - total_depenses

    recent_result = await session.execute(
        select(Document)
        .options(selectinload(Document.correspondent), selectinload(Document.document_type), selectinload(Document.tags))
        .order_by(Document.created_at.desc())
        .limit(5)
    )

    return templates.TemplateResponse(request, "pages/dashboard.html", {
        "now": today,
        "current_year": today.year,
        "total_depenses": total_depenses,
        "total_recettes": total_recettes,
        "solde": solde,
        "solde_color": "green" if solde >= 0 else "red",
        "no_type_count": no_type_count,
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
            func.coalesce(
                func.sum(Document.amount_ttc).filter(Document.category == CategoryEnum.recette),
                0,
            ).label("total_recettes"),
            func.coalesce(
                func.sum(Document.amount_ttc).filter(Document.category == CategoryEnum.depense),
                0,
            ).label("total_depenses"),
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

    docs_depenses = [d for d in docs if d.category == CategoryEnum.depense]
    docs_recettes = [d for d in docs if d.category == CategoryEnum.recette]
    docs_autres   = [d for d in docs if d.category == CategoryEnum.autre]

    total_depenses = sum((d.amount_ttc for d in docs_depenses if d.amount_ttc), Decimal("0"))
    total_recettes = sum((d.amount_ttc for d in docs_recettes if d.amount_ttc), Decimal("0"))

    return templates.TemplateResponse(request, "pages/year.html", {
        "year": year,
        "documents": docs,
        "docs_depenses": docs_depenses,
        "docs_recettes": docs_recettes,
        "docs_autres": docs_autres,
        "total_depenses": total_depenses,
        "total_recettes": total_recettes,
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
    no_type: bool = Query(default=False),
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
    if no_type:
        stmt = stmt.where(Document.document_type_id.is_(None))
    if no_correspondent:
        stmt = stmt.where(Document.correspondent_id.is_(None))
    if search and search.strip():
        stmt = stmt.where(Document.title.ilike(f"%{search.strip()}%"))
    stmt = stmt.order_by(Document.document_date.desc(), Document.created_at.desc())
    docs = list((await session.execute(stmt)).scalars().all())

    if no_type:
        back_url = "/documents?no_type=1"
    elif no_correspondent:
        back_url = "/documents?no_correspondent=1"
    else:
        back_url = "/documents"

    return templates.TemplateResponse(request, "pages/documents.html", {
        "documents": docs,
        "no_type": no_type,
        "no_correspondent": no_correspondent,
        "search": search or "",
        "back_url_encoded": quote(back_url, safe=""),
    })


# ── Édition document ──────────────────────────────────────────────────────────

@router.get("/documents/{id}/edit", response_class=HTMLResponse)
async def document_edit(
    id: uuid.UUID,
    request: Request,
    back: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    doc = await _doc_or_404(session, id)
    back_url = back if back and back.startswith("/") else f"/year/{doc.document_date.year}"
    all_tags_list = await _tags(session)
    return templates.TemplateResponse(request, "pages/document_edit.html", {
        "doc": doc,
        "back_url": back_url,
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

    cat_val = str(form.get("category", "")).strip()
    if cat_val in (c.value for c in CategoryEnum):
        doc.category = CategoryEnum(cat_val)

    is_autre = doc.category == CategoryEnum.autre
    doc.payment_date = None if is_autre else _date(str(form.get("payment_date", "")))
    doc.amount_ht = None if is_autre else _decimal(str(form.get("amount_ht", "")))
    doc.vat_amount = None if is_autre else _decimal(str(form.get("vat_amount", "")))
    doc.vat_rate = None if is_autre else _decimal(str(form.get("vat_rate", "")))
    doc.amount_ttc = None if is_autre else _decimal(str(form.get("amount_ttc", "")))
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
    back = str(form.get("back", "")).strip()
    redirect_url = back if back and back.startswith("/") else f"/year/{doc.document_date.year}"
    return RedirectResponse(redirect_url, status_code=303)


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
    remaining = await session.scalar(
        select(func.count(Document.id)).where(extract("year", Document.document_date) == year)
    )
    return RedirectResponse(f"/year/{year}" if remaining else "/years", status_code=303)


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
