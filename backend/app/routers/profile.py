import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services.auth_service import hash_password, verify_password
from app.templating import render

router = APIRouter(tags=["profile"])



@router.get("/profile")
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> object:
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    return render(request, "pages/profile.html", {
        "user": user,
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
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return RedirectResponse("/profile?error=invalid_email", status_code=303)
        if email != user.email:
            user.gmail_client_id = None
            user.gmail_client_secret = None
            user.gmail_refresh_token = None
            user.gmail_oauth_state = None
            user.gmail_code_verifier = None
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


@router.post("/profile/purge-data")
async def purge_data(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    form = await request.form()
    password = str(form.get("password", ""))
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect.")

    await session.execute(text("""
        TRUNCATE
            document_activity,
            document_tags,
            notifications,
            gmail_import_log,
            documents,
            correspondents,
            document_types,
            tags,
            reminders,
            gmail_sources
        RESTART IDENTITY CASCADE
    """))
    await session.commit()

    storage = Path(settings.storage_path).resolve()
    if storage.exists():
        for item in storage.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    return {"status": "ok"}


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
