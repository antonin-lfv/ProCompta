import asyncio
import uuid
from pathlib import Path

from app.config import settings

IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}


def _render_pdf_preview(pdf_path: str, document_id: uuid.UUID) -> str:
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
    relative = f"previews/{document_id}.png"
    out = Path(settings.storage_path) / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(str(out), "PNG")
    return relative


def _render_image_preview(image_path: str, document_id: uuid.UUID) -> str:
    from PIL import Image

    img = Image.open(image_path)
    img.thumbnail((1200, 1600))
    relative = f"previews/{document_id}.png"
    out = Path(settings.storage_path) / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG")
    return relative


async def generate_preview(file_path: str, document_id: uuid.UUID, mime_type: str = "application/pdf") -> str:
    loop = asyncio.get_event_loop()
    if mime_type in IMAGE_MIME_TYPES:
        return await loop.run_in_executor(None, _render_image_preview, file_path, document_id)
    return await loop.run_in_executor(None, _render_pdf_preview, file_path, document_id)


def delete_preview(document_id: uuid.UUID) -> None:
    (Path(settings.storage_path) / f"previews/{document_id}.png").unlink(missing_ok=True)
