#!/usr/bin/env python3
"""
One-shot migration: rename existing storage files to the new structure.
Old: documents/{uuid}.ext
New: {year}/{date}_{slug}_{short_id}.ext

Run inside the container:
  docker-compose exec api python migrate_storage.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.document import Document
from app.services.file_service import build_file_path, rename_file


async def migrate() -> None:
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        result = await session.execute(select(Document))
        docs = result.scalars().all()

        migrated = 0
        skipped = 0
        for doc in docs:
            expected = build_file_path(doc.id, doc.document_date, doc.title, doc.mime_type)
            if doc.file_path == expected:
                skipped += 1
                continue

            new_path = rename_file(doc.file_path, doc.id, doc.document_date, doc.title, doc.mime_type)
            print(f"  {doc.file_path!r:60s} → {new_path!r}")
            doc.file_path = new_path
            migrated += 1

        if migrated:
            await session.commit()
            print(f"\n✓ {migrated} fichier(s) migré(s), {skipped} déjà à jour.")
        else:
            print(f"Rien à migrer - {skipped} fichier(s) déjà à jour.")

    await engine.dispose()


asyncio.run(migrate())
