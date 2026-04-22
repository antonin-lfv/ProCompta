import hashlib
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import settings

ALLOWED_MIME_TYPES = {"application/pdf"}


async def save_uploaded_file(file: UploadFile, document_id: uuid.UUID) -> tuple[str, str, int]:
    """Read, hash and persist an uploaded file. Returns (relative_path, sha256, size)."""
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)

    relative_path = f"documents/{document_id}.pdf"
    full_path = Path(settings.storage_path) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(full_path, "wb") as f:
        await f.write(content)

    return relative_path, file_hash, file_size


def delete_file(relative_path: str) -> None:
    (Path(settings.storage_path) / relative_path).unlink(missing_ok=True)
