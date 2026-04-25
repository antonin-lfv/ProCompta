import hashlib
import uuid
from datetime import date
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import settings
from app.utils import slugify

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}

_MIME_EXT = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def build_file_path(document_id: uuid.UUID, document_date: date, title: str, mime: str) -> str:
    ext = _MIME_EXT.get(mime, ".bin")
    slug = (slugify(title)[:40].strip("-") or "document")
    short_id = str(document_id)[:8]
    return f"{document_date.year}/{document_date.isoformat()}_{slug}_{short_id}{ext}"


async def save_file_bytes(
    content: bytes,
    document_id: uuid.UUID,
    document_date: date,
    title: str,
    mime: str,
) -> str:
    relative_path = build_file_path(document_id, document_date, title, mime)
    full_path = Path(settings.storage_path) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(full_path, "wb") as f:
        await f.write(content)
    return relative_path


def rename_file(old_path: str, document_id: uuid.UUID, new_date: date, new_title: str, mime: str) -> str:
    """Move/rename file when title or date changes. Returns the new relative path."""
    new_path = build_file_path(document_id, new_date, new_title, mime)
    if old_path == new_path:
        return old_path
    old_full = Path(settings.storage_path) / old_path
    new_full = Path(settings.storage_path) / new_path
    new_full.parent.mkdir(parents=True, exist_ok=True)
    if old_full.exists():
        old_full.rename(new_full)
    return new_path


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def delete_file(relative_path: str) -> None:
    (Path(settings.storage_path) / relative_path).unlink(missing_ok=True)
