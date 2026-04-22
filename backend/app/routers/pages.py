from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.document import Document, document_tags
from app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    today = date.today()

    total, year_count, month_count, no_tags_count, no_correspondent_count = [
        (await session.scalar(q)) or 0
        for q in [
            select(func.count(Document.id)),
            select(func.count(Document.id)).where(
                extract("year", Document.document_date) == today.year
            ),
            select(func.count(Document.id)).where(
                extract("year", Document.document_date) == today.year,
                extract("month", Document.document_date) == today.month,
            ),
            select(func.count(Document.id)).where(
                ~Document.id.in_(select(document_tags.c.document_id))
            ),
            select(func.count(Document.id)).where(Document.correspondent_id.is_(None)),
        ]
    ]

    recent_result = await session.execute(
        select(Document)
        .options(
            selectinload(Document.correspondent),
            selectinload(Document.document_type),
            selectinload(Document.tags),
        )
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
