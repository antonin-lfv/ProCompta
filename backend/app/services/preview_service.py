import asyncio
import uuid
from pathlib import Path

from app.config import settings


def _render_preview(pdf_path: str, document_id: uuid.UUID) -> str:
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
    relative = f"previews/{document_id}.png"
    out = Path(settings.storage_path) / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(str(out), "PNG")
    return relative


async def generate_preview(pdf_path: str, document_id: uuid.UUID) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _render_preview, pdf_path, document_id)


def delete_preview(document_id: uuid.UUID) -> None:
    (Path(settings.storage_path) / f"previews/{document_id}.png").unlink(missing_ok=True)
