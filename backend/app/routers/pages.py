import csv
import io
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import asc as sa_asc, case, desc as sa_desc, extract, func, select
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


# Montant EUR effectif : amount_ttc si EUR, sinon amount_ttc_eur
_eur_amount = case(
    (Document.currency == "EUR", Document.amount_ttc),
    else_=Document.amount_ttc_eur,
)

_CAT_LABELS = {"depense": "Dépenses", "recette": "Recettes", "autre": "Autres"}
_CAT_ORDER  = {"depense": 0, "recette": 1, "autre": 2}


_SORT_COLS: dict[str, object] = {
    "date":          Document.document_date,
    "title":         Document.title,
    "amount":        _eur_amount,
    "correspondent": Correspondent.name,
}


def _sort_base_url(path: str, params: list[tuple[str, str]]) -> str:
    qs = urlencode([(k, v) for k, v in params if v])
    return path + "?" + (qs + "&" if qs else "")


def _variation(current: Decimal, prev: Decimal, *, higher_is_better: bool = True) -> dict | None:
    if not prev:
        return None
    pct = float((current - prev) / abs(prev) * 100)
    sign = "+" if pct > 0 else ""
    good = (pct > 0) == higher_is_better
    return {"text": f"{sign}{pct:.1f}% vs N-1", "color": "green" if good else "red"}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    today = date.today()
    _na   = Document.archived == False
    _year_filter      = (extract("year", Document.document_date) == today.year,     _na)
    _prev_year_filter = (extract("year", Document.document_date) == today.year - 1, _na)

    no_type_count, no_correspondent_count = [
        (await session.scalar(q)) or 0
        for q in [
            select(func.count(Document.id)).where(_na, Document.document_type_id.is_(None)),
            select(func.count(Document.id)).where(_na, Document.correspondent_id.is_(None)),
        ]
    ]

    total_depenses = (await session.scalar(
        select(func.sum(_eur_amount)).where(*_year_filter, Document.category == CategoryEnum.depense)
    )) or Decimal("0")
    total_recettes = (await session.scalar(
        select(func.sum(_eur_amount)).where(*_year_filter, Document.category == CategoryEnum.recette)
    )) or Decimal("0")
    solde = total_recettes - total_depenses

    # TVA
    tva_deductible = (await session.scalar(
        select(func.sum(Document.vat_amount)).where(*_year_filter, Document.category == CategoryEnum.depense)
    )) or Decimal("0")
    tva_collectee = (await session.scalar(
        select(func.sum(Document.vat_amount)).where(*_year_filter, Document.category == CategoryEnum.recette)
    )) or Decimal("0")

    # N-1
    prev_depenses = (await session.scalar(
        select(func.sum(_eur_amount)).where(*_prev_year_filter, Document.category == CategoryEnum.depense)
    )) or Decimal("0")
    prev_recettes = (await session.scalar(
        select(func.sum(_eur_amount)).where(*_prev_year_filter, Document.category == CategoryEnum.recette)
    )) or Decimal("0")
    prev_solde = prev_recettes - prev_depenses

    # Données mensuelles pour le graphique
    monthly_result = await session.execute(
        select(
            extract("month", Document.document_date).label("month"),
            func.coalesce(func.sum(_eur_amount).filter(Document.category == CategoryEnum.depense), 0).label("depenses"),
            func.coalesce(func.sum(_eur_amount).filter(Document.category == CategoryEnum.recette), 0).label("recettes"),
        )
        .where(*_year_filter)
        .group_by(extract("month", Document.document_date))
        .order_by(extract("month", Document.document_date))
    )
    monthly_map = {int(r.month): r for r in monthly_result.all()}
    monthly_depenses = [float(monthly_map[m].depenses if m in monthly_map else 0) for m in range(1, 13)]
    monthly_recettes = [float(monthly_map[m].recettes if m in monthly_map else 0) for m in range(1, 13)]

    # Répartition dépenses par type de document
    type_result = await session.execute(
        select(
            DocumentType.name,
            DocumentType.color,
            func.coalesce(func.sum(_eur_amount), 0).label("total"),
        )
        .join(Document, Document.document_type_id == DocumentType.id)
        .where(*_year_filter, Document.category == CategoryEnum.depense)
        .group_by(DocumentType.id, DocumentType.name, DocumentType.color)
        .order_by(func.sum(_eur_amount).desc())
    )
    type_depenses = [
        {"name": r.name, "color": r.color or "#6366f1", "total": float(r.total)}
        for r in type_result.all()
    ]

    # Top 5 correspondants par dépenses
    top_corr_result = await session.execute(
        select(
            Correspondent.name,
            func.coalesce(func.sum(_eur_amount), 0).label("total"),
        )
        .join(Document, Document.correspondent_id == Correspondent.id)
        .where(*_year_filter, Document.category == CategoryEnum.depense)
        .group_by(Correspondent.id, Correspondent.name)
        .order_by(func.sum(_eur_amount).desc())
        .limit(5)
    )
    top_correspondants = [
        {"name": r.name, "total": float(r.total)}
        for r in top_corr_result.all()
    ]

    recent_result = await session.execute(
        select(Document)
        .options(selectinload(Document.correspondent), selectinload(Document.document_type), selectinload(Document.tags))
        .where(_na)
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
        "tva_deductible": tva_deductible,
        "tva_collectee": tva_collectee,
        "depenses_var": _variation(total_depenses, prev_depenses, higher_is_better=False),
        "recettes_var": _variation(total_recettes, prev_recettes, higher_is_better=True),
        "solde_var":    _variation(solde, prev_solde, higher_is_better=True),
        "monthly_depenses": monthly_depenses,
        "monthly_recettes": monthly_recettes,
        "type_depenses": type_depenses,
        "top_correspondants": top_correspondants,
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
                func.sum(_eur_amount).filter(Document.category == CategoryEnum.recette),
                0,
            ).label("total_recettes"),
            func.coalesce(
                func.sum(_eur_amount).filter(Document.category == CategoryEnum.depense),
                0,
            ).label("total_depenses"),
        )
        .where(Document.archived == False)
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
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    amount_min: str | None = Query(default=None),
    amount_max: str | None = Query(default=None),
    sort: str = Query(default="date"),
    order: str = Query(default="desc"),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    corr_uuid = _uuid(correspondent_id)
    dtype_uuid = _uuid(document_type_id)
    tag_uuids = [u for s in tag_ids if (u := _uuid(s))]
    _date_from = _date(date_from)
    _date_to = _date(date_to)
    _amount_min = _decimal(amount_min)
    _amount_max = _decimal(amount_max)

    if sort not in _SORT_COLS:
        sort = "date"
    if order not in ("asc", "desc"):
        order = "desc"
    order_fn = sa_desc if order == "desc" else sa_asc

    stmt = (
        select(Document)
        .options(selectinload(Document.tags), selectinload(Document.correspondent), selectinload(Document.document_type))
        .outerjoin(Correspondent, Document.correspondent_id == Correspondent.id)
        .where(extract("year", Document.document_date) == year, Document.archived == False)
    )
    if corr_uuid:
        stmt = stmt.where(Document.correspondent_id == corr_uuid)
    if dtype_uuid:
        stmt = stmt.where(Document.document_type_id == dtype_uuid)
    if search and search.strip():
        stmt = stmt.where(Document.title.ilike(f"%{search.strip()}%"))
    if _date_from:
        stmt = stmt.where(Document.document_date >= _date_from)
    if _date_to:
        stmt = stmt.where(Document.document_date <= _date_to)
    if _amount_min is not None:
        stmt = stmt.where(_eur_amount >= _amount_min)
    if _amount_max is not None:
        stmt = stmt.where(_eur_amount <= _amount_max)
    for tid in tag_uuids:
        stmt = stmt.where(Document.id.in_(
            select(document_tags.c.document_id).where(document_tags.c.tag_id == tid)
        ))
    if sort == "date":
        stmt = stmt.order_by(order_fn(_SORT_COLS["date"]))
    else:
        stmt = stmt.order_by(order_fn(_SORT_COLS[sort]), sa_desc(Document.document_date))

    docs = list((await session.execute(stmt)).scalars().all())

    docs_depenses = [d for d in docs if d.category == CategoryEnum.depense]
    docs_recettes = [d for d in docs if d.category == CategoryEnum.recette]
    docs_autres   = [d for d in docs if d.category == CategoryEnum.autre]

    archived_stmt = (
        select(Document)
        .options(selectinload(Document.tags), selectinload(Document.correspondent), selectinload(Document.document_type))
        .outerjoin(Correspondent, Document.correspondent_id == Correspondent.id)
        .where(extract("year", Document.document_date) == year, Document.archived == True)
    )
    if corr_uuid:
        archived_stmt = archived_stmt.where(Document.correspondent_id == corr_uuid)
    if search and search.strip():
        archived_stmt = archived_stmt.where(Document.title.ilike(f"%{search.strip()}%"))
    if _date_from:
        archived_stmt = archived_stmt.where(Document.document_date >= _date_from)
    if _date_to:
        archived_stmt = archived_stmt.where(Document.document_date <= _date_to)
    if _amount_min is not None:
        archived_stmt = archived_stmt.where(_eur_amount >= _amount_min)
    if _amount_max is not None:
        archived_stmt = archived_stmt.where(_eur_amount <= _amount_max)
    archived_stmt = archived_stmt.order_by(Document.document_date.desc())
    docs_archived = list((await session.execute(archived_stmt)).scalars().all())

    def _eur(d: Document) -> Decimal:
        return (d.amount_ttc if d.currency == "EUR" else d.amount_ttc_eur) or Decimal("0")

    total_depenses = sum((_eur(d) for d in docs_depenses), Decimal("0"))
    total_recettes = sum((_eur(d) for d in docs_recettes), Decimal("0"))
    has_foreign_currency = any(
        d.currency != "EUR" and not d.amount_ttc_eur for d in docs
    )

    _filter_params: list[tuple[str, str]] = [
        ("correspondent_id", str(corr_uuid) if corr_uuid else ""),
        ("document_type_id", str(dtype_uuid) if dtype_uuid else ""),
        ("search", search or ""),
        ("date_from", date_from or ""),
        ("date_to", date_to or ""),
        ("amount_min", amount_min or ""),
        ("amount_max", amount_max or ""),
        *[("tag_ids", str(t)) for t in tag_uuids],
    ]

    return templates.TemplateResponse(request, "pages/year.html", {
        "year": year,
        "documents": docs,
        "docs_depenses": docs_depenses,
        "docs_recettes": docs_recettes,
        "docs_autres": docs_autres,
        "docs_archived": docs_archived,
        "total_depenses": total_depenses,
        "total_recettes": total_recettes,
        "has_foreign_currency": has_foreign_currency,
        "correspondents": await _correspondents(session),
        "doc_types": await _doc_types(session),
        "all_tags": await _tags(session),
        "filters": {
            "correspondent_id": str(corr_uuid) if corr_uuid else "",
            "document_type_id": str(dtype_uuid) if dtype_uuid else "",
            "tag_ids": [str(t) for t in tag_uuids],
            "search": search or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
            "amount_min": amount_min or "",
            "amount_max": amount_max or "",
        },
        "has_filters": any([corr_uuid, dtype_uuid, tag_uuids, search, _date_from, _date_to, _amount_min, _amount_max]),
        "sort": sort,
        "order": order,
        "sort_base_url": _sort_base_url(f"/year/{year}", _filter_params),
    })


# ── Tous les documents ───────────────────────────────────────────────────────

_PAGE_SIZE = 50


@router.get("/documents", response_class=HTMLResponse)
async def documents_list(
    request: Request,
    no_type: bool = Query(default=False),
    no_correspondent: bool = Query(default=False),
    show_archived: bool = Query(default=False),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    amount_min: str | None = Query(default=None),
    amount_max: str | None = Query(default=None),
    sort: str = Query(default="date"),
    order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    if sort not in _SORT_COLS:
        sort = "date"
    if order not in ("asc", "desc"):
        order = "desc"
    order_fn = sa_desc if order == "desc" else sa_asc

    _date_from = _date(date_from)
    _date_to = _date(date_to)
    _amount_min = _decimal(amount_min)
    _amount_max = _decimal(amount_max)

    base_where = [Document.archived == show_archived]
    if no_type:
        base_where.append(Document.document_type_id.is_(None))
    if no_correspondent:
        base_where.append(Document.correspondent_id.is_(None))
    if search and search.strip():
        base_where.append(Document.title.ilike(f"%{search.strip()}%"))
    if _date_from:
        base_where.append(Document.document_date >= _date_from)
    if _date_to:
        base_where.append(Document.document_date <= _date_to)
    if _amount_min is not None:
        base_where.append(_eur_amount >= _amount_min)
    if _amount_max is not None:
        base_where.append(_eur_amount <= _amount_max)

    total = (await session.scalar(
        select(func.count(Document.id))
        .outerjoin(Correspondent, Document.correspondent_id == Correspondent.id)
        .where(*base_where)
    )) or 0
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = min(page, total_pages)

    stmt = (
        select(Document)
        .options(selectinload(Document.tags), selectinload(Document.correspondent), selectinload(Document.document_type))
        .outerjoin(Correspondent, Document.correspondent_id == Correspondent.id)
        .where(*base_where)
    )
    if sort == "date":
        stmt = stmt.order_by(order_fn(_SORT_COLS["date"]))
    else:
        stmt = stmt.order_by(order_fn(_SORT_COLS[sort]), sa_desc(Document.document_date))
    stmt = stmt.offset((page - 1) * _PAGE_SIZE).limit(_PAGE_SIZE)
    docs = list((await session.execute(stmt)).scalars().all())

    back_params = [(k, v) for k, v in [
        ("no_type", "1" if no_type else ""),
        ("no_correspondent", "1" if no_correspondent else ""),
        ("show_archived", "1" if show_archived else ""),
        ("search", search or ""),
        ("date_from", date_from or ""),
        ("date_to", date_to or ""),
        ("amount_min", amount_min or ""),
        ("amount_max", amount_max or ""),
    ] if v]
    back_url = "/documents" + ("?" + urlencode(back_params) if back_params else "")

    _filter_params: list[tuple[str, str]] = [
        ("no_type", "1" if no_type else ""),
        ("no_correspondent", "1" if no_correspondent else ""),
        ("show_archived", "1" if show_archived else ""),
        ("search", search or ""),
        ("date_from", date_from or ""),
        ("date_to", date_to or ""),
        ("amount_min", amount_min or ""),
        ("amount_max", amount_max or ""),
    ]

    return templates.TemplateResponse(request, "pages/documents.html", {
        "documents": docs,
        "no_type": no_type,
        "no_correspondent": no_correspondent,
        "show_archived": show_archived,
        "search": search or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "amount_min": amount_min or "",
        "amount_max": amount_max or "",
        "has_filters": any([_date_from, _date_to, _amount_min, _amount_max, search]),
        "back_url_encoded": quote(back_url, safe=""),
        "sort": sort,
        "order": order,
        "sort_base_url": _sort_base_url("/documents", _filter_params),
        "page": page,
        "total_pages": total_pages,
        "total": total,
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
    doc.amount_ttc_eur = None if (is_autre or doc.currency == "EUR") else _decimal(str(form.get("amount_ttc_eur", "")))
    doc.notes = str(form.get("notes", "")).strip()[:250] or None
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


# ── Rapports ──────────────────────────────────────────────────────────────────

@router.get("/reports", response_class=HTMLResponse)
async def reports(
    request: Request,
    year: int | None = Query(default=None),
    quarter: int | None = Query(default=None, ge=1, le=4),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    today = date.today()

    years_result = await session.execute(
        select(extract("year", Document.document_date).label("year"))
        .where(Document.archived == False)
        .distinct()
        .order_by(extract("year", Document.document_date).desc())
    )
    available_years = [int(r.year) for r in years_result.all()]
    if year is None:
        year = today.year if today.year in available_years else (available_years[0] if available_years else today.year)

    _base = [extract("year", Document.document_date) == year, Document.archived == False]
    if quarter:
        _base.append(extract("quarter", Document.document_date) == quarter)

    _Q_SUFFIX = {1: " · T1", 2: " · T2", 3: " · T3", 4: " · T4"}
    period_label = str(year) + (_Q_SUFFIX.get(quarter, "") if quarter else "")

    # Bilan annuel : catégorie × type de document
    bilan_result = await session.execute(
        select(
            Document.category,
            DocumentType.name.label("type_name"),
            func.count(Document.id).label("count"),
            func.coalesce(func.sum(Document.amount_ht), 0).label("total_ht"),
            func.coalesce(func.sum(Document.vat_amount), 0).label("total_tva"),
            func.coalesce(func.sum(_eur_amount), 0).label("total_ttc"),
        )
        .outerjoin(DocumentType, Document.document_type_id == DocumentType.id)
        .where(*_base)
        .group_by(Document.category, DocumentType.id, DocumentType.name)
        .order_by(Document.category, DocumentType.name)
    )
    bilan_rows = [
        {
            "category":  r.category.value,
            "type_name": r.type_name or "(sans type)",
            "count":     int(r.count),
            "total_ht":  float(r.total_ht or 0),
            "total_tva": float(r.total_tva or 0),
            "total_ttc": float(r.total_ttc or 0),
        }
        for r in bilan_result.all()
    ]
    bilan_rows.sort(key=lambda r: (_CAT_ORDER.get(r["category"], 3), r["type_name"]))

    # Bilan par correspondant : pivot dépenses / recettes
    corr_result = await session.execute(
        select(
            Correspondent.name.label("corr_name"),
            Document.category,
            func.count(Document.id).label("count"),
            func.coalesce(func.sum(Document.amount_ht), 0).label("total_ht"),
            func.coalesce(func.sum(Document.vat_amount), 0).label("total_tva"),
            func.coalesce(func.sum(_eur_amount), 0).label("total_ttc"),
        )
        .outerjoin(Correspondent, Document.correspondent_id == Correspondent.id)
        .where(*_base)
        .group_by(Correspondent.id, Correspondent.name, Document.category)
        .order_by(Correspondent.name, Document.category)
    )
    _corr_pivot: dict[str, dict] = defaultdict(lambda: {
        "depenses": {"count": 0, "ht": 0.0, "tva": 0.0, "ttc": 0.0},
        "recettes": {"count": 0, "ht": 0.0, "tva": 0.0, "ttc": 0.0},
    })
    for r in corr_result.all():
        name = r.corr_name or "(sans correspondant)"
        if r.category == CategoryEnum.depense:
            _corr_pivot[name]["depenses"] = {"count": int(r.count), "ht": float(r.total_ht or 0), "tva": float(r.total_tva or 0), "ttc": float(r.total_ttc or 0)}
        elif r.category == CategoryEnum.recette:
            _corr_pivot[name]["recettes"] = {"count": int(r.count), "ht": float(r.total_ht or 0), "tva": float(r.total_tva or 0), "ttc": float(r.total_ttc or 0)}
    corr_rows = [
        {
            "name":     name,
            "depenses": data["depenses"],
            "recettes": data["recettes"],
            "solde":    data["recettes"]["ttc"] - data["depenses"]["ttc"],
        }
        for name, data in sorted(_corr_pivot.items(), key=lambda x: x[0].lower())
    ]

    return templates.TemplateResponse(request, "pages/reports.html", {
        "year": year,
        "quarter": quarter,
        "period_label": period_label,
        "available_years": available_years,
        "bilan_rows": bilan_rows,
        "corr_rows": corr_rows,
    })


@router.get("/reports/export/documents")
async def export_documents_csv(
    year: int = Query(...),
    quarter: int | None = Query(default=None, ge=1, le=4),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    _base = [extract("year", Document.document_date) == year, Document.archived == False]
    if quarter:
        _base.append(extract("quarter", Document.document_date) == quarter)

    result = await session.execute(
        select(Document)
        .options(
            selectinload(Document.correspondent),
            selectinload(Document.document_type),
            selectinload(Document.tags),
        )
        .where(*_base)
        .order_by(Document.document_date.desc())
    )
    docs = result.scalars().all()

    suffix = f"_T{quarter}" if quarter else ""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Titre", "Date", "Date paiement", "Catégorie", "Correspondant", "Type", "Tags", "Devise", "HT", "TVA", "TTC", "TTC EUR", "Notes"])
    for doc in docs:
        writer.writerow([
            doc.title,
            doc.document_date.isoformat() if doc.document_date else "",
            doc.payment_date.isoformat() if doc.payment_date else "",
            _CAT_LABELS.get(doc.category.value, doc.category.value),
            doc.correspondent.name if doc.correspondent else "",
            doc.document_type.name if doc.document_type else "",
            ", ".join(t.name for t in doc.tags),
            doc.currency,
            str(doc.amount_ht or ""),
            str(doc.vat_amount or ""),
            str(doc.amount_ttc or ""),
            str(doc.amount_ttc_eur or ""),
            doc.notes or "",
        ])
    content = "﻿" + output.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="procompta_{year}{suffix}_documents.csv"'},
    )


@router.get("/reports/export/bilan")
async def export_bilan_csv(
    year: int = Query(...),
    quarter: int | None = Query(default=None, ge=1, le=4),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    _base = [extract("year", Document.document_date) == year, Document.archived == False]
    if quarter:
        _base.append(extract("quarter", Document.document_date) == quarter)

    result = await session.execute(
        select(
            Document.category,
            DocumentType.name.label("type_name"),
            Correspondent.name.label("corr_name"),
            func.count(Document.id).label("count"),
            func.coalesce(func.sum(Document.amount_ht), 0).label("total_ht"),
            func.coalesce(func.sum(Document.vat_amount), 0).label("total_tva"),
            func.coalesce(func.sum(_eur_amount), 0).label("total_ttc"),
        )
        .outerjoin(DocumentType, Document.document_type_id == DocumentType.id)
        .outerjoin(Correspondent, Document.correspondent_id == Correspondent.id)
        .where(*_base)
        .group_by(Document.category, DocumentType.id, DocumentType.name, Correspondent.id, Correspondent.name)
        .order_by(Document.category, DocumentType.name, Correspondent.name)
    )
    rows = result.all()

    suffix = f"_T{quarter}" if quarter else ""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Catégorie", "Type", "Correspondant", "Nb documents", "Total HT (€)", "Total TVA (€)", "Total TTC (€)"])
    for r in rows:
        writer.writerow([
            _CAT_LABELS.get(r.category.value, r.category.value),
            r.type_name or "(sans type)",
            r.corr_name or "(sans correspondant)",
            r.count,
            f"{float(r.total_ht or 0):.2f}",
            f"{float(r.total_tva or 0):.2f}",
            f"{float(r.total_ttc or 0):.2f}",
        ])
    content = "﻿" + output.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="procompta_{year}{suffix}_bilan.csv"'},
    )


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
