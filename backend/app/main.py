from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import correspondents, document_types, documents, pages, tags

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
