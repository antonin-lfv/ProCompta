import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import async_session_factory
from app.middleware.auth import AuthMiddleware
from app.models.user import User
from app.models.document_type import DocumentType
from app.models.tag import Tag
from app.routers import auth, backup, correspondents, document_types, documents, notifications, pages, profile, tags
from app.routers.backup import save_backup_to_disk
from app.services.auth_service import hash_password
from app.templating import app_version, templates

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


async def _auto_backup() -> None:
    backup_dir = Path(settings.backup_path)
    existing = sorted(backup_dir.glob("procompta_backup_*.zip"))
    if existing:
        last_mtime = datetime.fromtimestamp(existing[-1].stat().st_mtime)
        if (datetime.now() - last_mtime).days < 7:
            return
    try:
        await asyncio.to_thread(save_backup_to_disk)
        logger.info("Backup automatique créé avec succès")
    except Exception:
        logger.exception("Échec du backup automatique au démarrage")


async def _create_admin_user() -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(User))
        if existing is None:
            session.add(User(
                name=settings.admin_name,
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
            ))
            await session.commit()


async def _seed_defaults() -> None:
    async with async_session_factory() as session:
        if not await session.scalar(select(DocumentType)):
            session.add_all([
                DocumentType(name="Facture",             slug="facture",             color="#6366f1"),
                DocumentType(name="Devis",               slug="devis",               color="#8b5cf6"),
                DocumentType(name="Contrat",             slug="contrat",             color="#ec4899"),
                DocumentType(name="Bon de commande",     slug="bon-de-commande",     color="#f97316"),
                DocumentType(name="Relevé",              slug="releve",              color="#06b6d4"),
                DocumentType(name="Reçu",                slug="recu",                color="#10b981"),
                DocumentType(name="Bulletin de salaire", slug="bulletin-de-salaire", color="#84cc16"),
                DocumentType(name="Rapport",             slug="rapport",             color="#64748b"),
                DocumentType(name="Avenant",             slug="avenant",             color="#f59e0b"),
                DocumentType(name="Attestation",         slug="attestation",         color="#14b8a6"),
                DocumentType(name="Avoir",               slug="avoir",               color="#a855f7"),
                DocumentType(name="Bordereau",           slug="bordereau",           color="#78716c"),
            ])
        if not await session.scalar(select(Tag)):
            session.add_all([
                Tag(name="Urgent",      slug="urgent",      color="#ef4444"),
                Tag(name="À payer",     slug="a-payer",     color="#f97316"),
                Tag(name="Payé",        slug="paye",        color="#10b981"),
                Tag(name="À vérifier", slug="a-verifier",  color="#eab308"),
                Tag(name="Important",   slug="important",   color="#6366f1"),
            ])
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _create_admin_user()
    await _seed_defaults()
    await _auto_backup()
    yield


app = FastAPI(title="ProCompta", version="0.1.0", lifespan=lifespan)


_ERROR_MESSAGES = {
    400: ("Requête invalide", "Les données envoyées sont incorrectes ou incomplètes."),
    403: ("Accès refusé", "Vous n'avez pas les droits pour accéder à cette ressource."),
    404: ("Page introuvable", "La page que vous cherchez n'existe pas ou a été déplacée."),
    405: ("Méthode non autorisée", "Cette action n'est pas permise sur cette ressource."),
    413: ("Fichier trop volumineux", "Le fichier envoyé dépasse la taille maximale autorisée."),
    422: ("Données invalides", "Le format des données envoyées n'est pas correct."),
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=500, content={"detail": "Erreur serveur interne"})
    title, message = _ERROR_MESSAGES[500]
    return templates.TemplateResponse(
        request,
        "pages/error.html",
        {"status_code": 500, "title": title, "message": message},
        status_code=500,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": app_version}
