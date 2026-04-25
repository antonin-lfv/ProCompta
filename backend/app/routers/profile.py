from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services.auth_service import hash_password, verify_password
from app.templating import render

router = APIRouter(tags=["profile"])

_CURRENCIES = ["EUR", "USD", "GBP", "CHF", "JPY", "CAD"]
_MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


@router.get("/profile")
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> object:
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    return render(request, "pages/profile.html", {
        "user": user,
        "currencies": _CURRENCIES,
        "months": _MONTHS,
        "success": success,
        "error": error,
    })


@router.post("/profile/identity")
async def update_identity(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    form = await request.form()
    name = str(form.get("name", "")).strip()
    email = str(form.get("email", "")).strip().lower()
    if name:
        user.name = name
    if email:
        user.email = email
    await session.commit()
    return RedirectResponse("/profile?success=identity", status_code=303)


@router.post("/profile/password")
async def update_password(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    form = await request.form()
    old_pw = str(form.get("old_password", ""))
    new_pw = str(form.get("new_password", ""))
    confirm_pw = str(form.get("confirm_password", ""))

    if not verify_password(old_pw, user.hashed_password):
        return RedirectResponse("/profile?error=wrong_password", status_code=303)
    if new_pw != confirm_pw:
        return RedirectResponse("/profile?error=password_mismatch", status_code=303)
    if len(new_pw) < 8:
        return RedirectResponse("/profile?error=password_too_short", status_code=303)

    user.hashed_password = hash_password(new_pw)
    await session.commit()
    return RedirectResponse("/profile?success=password", status_code=303)


@router.post("/profile/preferences")
async def update_preferences(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    form = await request.form()
    currency = str(form.get("default_currency", "EUR")).strip()
    if currency in _CURRENCIES:
        user.default_currency = currency
    try:
        month = int(form.get("fiscal_year_start", 1))
        if 1 <= month <= 12:
            user.fiscal_year_start = month
    except (ValueError, TypeError):
        pass
    await session.commit()
    return RedirectResponse("/profile?success=preferences", status_code=303)


@router.post("/profile/purge-previews")
async def purge_previews(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    previews_dir = Path(settings.storage_path) / "previews"
    if not previews_dir.exists():
        return {"deleted": 0}

    result = await session.execute(select(Document.id))
    existing_ids = {str(id_) for id_ in result.scalars().all()}

    deleted = 0
    for f in previews_dir.glob("*.png"):
        if f.stem not in existing_ids:
            f.unlink(missing_ok=True)
            deleted += 1

    return {"deleted": deleted}
