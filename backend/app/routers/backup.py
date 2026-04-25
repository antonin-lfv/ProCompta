import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/backup", tags=["backup"])


def _parse_db_url() -> dict:
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    p = urlparse(url)
    return {
        "host": p.hostname,
        "port": str(p.port or 5432),
        "user": p.username,
        "password": p.password or "",
        "dbname": p.path.lstrip("/"),
    }


@router.post("")
async def create_backup() -> dict:
    db = _parse_db_url()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"procompta_backup_{timestamp}.zip"
    backup_dir = Path(settings.backup_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    zip_path = backup_dir / filename

    # pg_dump
    result = subprocess.run(
        ["pg_dump", "-h", db["host"], "-p", db["port"], "-U", db["user"], db["dbname"]],
        capture_output=True,
        env={"PGPASSWORD": db["password"], "PATH": "/usr/bin:/bin"},
        timeout=120,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"pg_dump failed: {result.stderr.decode()}")

    sql_dump = result.stdout

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("database.sql", sql_dump)
        storage = Path(settings.storage_path)
        for file in storage.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=f"storage/{file.relative_to(storage)}")

    size_mb = round(zip_path.stat().st_size / 1_048_576, 2)
    return {"filename": filename, "size_mb": size_mb}
