from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import correspondents, document_types, documents, notifications, pages, tags
from app.templating import templates

app = FastAPI(title="ProCompta", version="0.1.0")

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

previews_dir = Path(settings.storage_path) / "previews"
previews_dir.mkdir(parents=True, exist_ok=True)
app.mount("/previews", StaticFiles(directory=previews_dir), name="previews")

app.include_router(pages.router)
app.include_router(correspondents.router, prefix="/api")
app.include_router(document_types.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")


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
    return {"status": "ok", "version": "0.1.0"}
