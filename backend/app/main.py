from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import async_session_factory, get_session
from app.middleware.auth import AuthMiddleware
from app.models.user import User
from app.routers import auth, backup, correspondents, document_types, documents, notifications, pages, profile, tags
from app.services.auth_service import hash_password
from app.templating import templates

app = FastAPI(title="ProCompta", version="0.1.0")

BASE_DIR = Path(__file__).parent

app.add_middleware(AuthMiddleware)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

previews_dir = Path(settings.storage_path) / "previews"
previews_dir.mkdir(parents=True, exist_ok=True)
app.mount("/previews", StaticFiles(directory=previews_dir), name="previews")

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(pages.router)
app.include_router(correspondents.router, prefix="/api")
app.include_router(document_types.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(backup.router, prefix="/api")


@app.on_event("startup")
async def create_admin_user() -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(User))
        if existing is None:
            session.add(User(
                name=settings.admin_name,
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
            ))
            await session.commit()


_ERROR_MESSAGES = {
    404: ("Page introuvable", "La page que vous cherchez n'existe pas ou a été déplacée."),
    403: ("Accès refusé", "Vous n'avez pas les droits pour accéder à cette ressource."),
    500: ("Erreur serveur", "Une erreur inattendue s'est produite. Réessayez dans un moment."),
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    title, message = _ERROR_MESSAGES.get(exc.status_code, ("Erreur", str(exc.detail)))
    return templates.TemplateResponse(
        request,
        "pages/error.html",
        {"status_code": exc.status_code, "title": title, "message": message},
        status_code=exc.status_code,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.6.1"}
