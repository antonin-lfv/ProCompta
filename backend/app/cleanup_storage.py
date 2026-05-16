#!/usr/bin/env python3
"""
Clean up storage files that have no matching document in the database.
Also removes orphaned preview files.

Dry-run by default — pass --delete to actually remove files.

Run inside the container:
  docker-compose exec api python app/cleanup_storage.py          # dry-run
  docker-compose exec api python app/cleanup_storage.py --delete # remove
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.document import Document

DRY_RUN = "--delete" not in sys.argv


async def cleanup() -> None:
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    storage = Path(settings.storage_path)
    previews_dir = storage / "previews"

    async with Session() as session:
        result = await session.execute(select(Document.file_path, Document.id))
        rows = result.all()

    known_paths = {r.file_path for r in rows if r.file_path}
    known_ids = {str(r.id) for r in rows}

    await engine.dispose()

    # --- Documents ---
    orphan_docs = []
    for f in storage.rglob("*"):
        if not f.is_file():
            continue
        if f.is_relative_to(previews_dir):
            continue
        rel = str(f.relative_to(storage))
        if rel not in known_paths:
            orphan_docs.append(f)

    # --- Previews ---
    orphan_previews = []
    if previews_dir.exists():
        for f in previews_dir.iterdir():
            if not f.is_file():
                continue
            # preview filenames: {uuid}.{ext}
            doc_id = f.stem
            if doc_id not in known_ids:
                orphan_previews.append(f)

    total = len(orphan_docs) + len(orphan_previews)

    if not total:
        print("Rien à nettoyer — tous les fichiers sont référencés en base.")
        return

    mode = "[DRY-RUN]" if DRY_RUN else "[DELETE]"

    if orphan_docs:
        print(f"\n{mode} Documents orphelins ({len(orphan_docs)}) :")
        for f in sorted(orphan_docs):
            print(f"  {f.relative_to(storage)}")
            if not DRY_RUN:
                f.unlink()

    if orphan_previews:
        print(f"\n{mode} Previews orphelines ({len(orphan_previews)}) :")
        for f in sorted(orphan_previews):
            print(f"  previews/{f.name}")
            if not DRY_RUN:
                f.unlink()

    if DRY_RUN:
        print(f"\n{total} fichier(s) seraient supprimés. Relance avec --delete pour confirmer.")
    else:
        print(f"\n✓ {total} fichier(s) supprimé(s).")


asyncio.run(cleanup())
