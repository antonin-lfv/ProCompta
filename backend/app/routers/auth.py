import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.user import User
from app.services.auth_service import _SESSION_MAX_AGE, create_token, verify_password
from app.templating import templates

router = APIRouter(tags=["auth"])

_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 10
_WINDOW = 60  # secondes


def _check_rate_limit(ip: str) -> bool:
    now = time.monotonic()
    recent = [t for t in _LOGIN_ATTEMPTS.get(ip, []) if now - t < _WINDOW]
    if not recent:
        _LOGIN_ATTEMPTS.pop(ip, None)  # purge stale entry
    if len(recent) >= _MAX_ATTEMPTS:
        _LOGIN_ATTEMPTS[ip] = recent
        return False
    recent.append(now)
    _LOGIN_ATTEMPTS[ip] = recent
    return True


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "pages/login.html", {})


@router.post("/login")
async def login(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        return templates.TemplateResponse(
            request, "pages/login.html",
            {"error": "Trop de tentatives. Réessayez dans une minute."},
            status_code=429,
        )

    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))

    user = await session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "pages/login.html",
            {"error": "Email ou mot de passe incorrect"},
            status_code=401,
        )

    token = create_token(str(user.id), settings.secret_key)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "procompta_session", token,
        httponly=True, max_age=_SESSION_MAX_AGE, samesite="lax",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("procompta_session")
    return response
