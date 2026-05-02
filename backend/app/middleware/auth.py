import uuid

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.database import async_session_factory
from app.models.user import User
from app.services.auth_service import verify_token

_EXEMPT_PATHS = {"/login", "/health", "/api/gmail/oauth/callback"}
_EXEMPT_PREFIXES = ("/static", "/previews")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _EXEMPT_PATHS or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        token = request.cookies.get("procompta_session")
        user_id = verify_token(token, settings.secret_key) if token else None

        if user_id is None:
            if path.startswith("/api"):
                return JSONResponse({"detail": "Non authentifié"}, status_code=401)
            return RedirectResponse("/login", status_code=302)

        async with async_session_factory() as session:
            user = await session.get(User, uuid.UUID(user_id))

        if user is None:
            if path.startswith("/api"):
                return JSONResponse({"detail": "Non authentifié"}, status_code=401)
            return RedirectResponse("/login", status_code=302)

        request.state.user = user
        return await call_next(request)
