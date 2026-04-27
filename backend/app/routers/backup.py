import io
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.config import settings
from app.database import async_session_factory, engine
from app.dependencies import get_current_user
from app.models.user import User
from app.services.auth_service import verify_password

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


def _psql_env(db: dict) -> dict:
    return {"PGPASSWORD": db["password"], "PATH": "/usr/bin:/bin:/usr/lib/postgresql/16/bin"}


@router.get("/download")
async def download_backup(
    request: Request,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    db = _parse_db_url()

    result = subprocess.run(
        ["pg_dump", "--clean", "--if-exists", "--exclude-table=users",
         "-h", db["host"], "-p", db["port"], "-U", db["user"], db["dbname"]],
        capture_output=True,
        env=_psql_env(db),
        timeout=120,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"pg_dump failed: {result.stderr.decode()}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("database.sql", result.stdout)
        storage = Path(settings.storage_path)
        for file in storage.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=f"storage/{file.relative_to(storage)}")
    buf.seek(0)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"procompta_backup_{timestamp}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def restore_backup(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
) -> dict:
    user: User = request.state.user
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Mot de passe incorrect")

    content = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Fichier zip invalide")

    if "database.sql" not in zf.namelist():
        raise HTTPException(status_code=400, detail="Archive invalide (database.sql manquant)")

    saved_user = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "hashed_password": user.hashed_password,
        "default_currency": user.default_currency,
        "fiscal_year_start": user.fiscal_year_start,
    }

    sql_dump = zf.read("database.sql")
    db = _parse_db_url()
    env = _psql_env(db)
    psql_base = ["psql", "-h", db["host"], "-p", db["port"], "-U", db["user"], db["dbname"]]

    clean = subprocess.run(
        psql_base + ["-c", f"DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO {db['user']};"],
        capture_output=True, env=env, timeout=30,
    )
    if clean.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Schema reset failed: {clean.stderr.decode()}")

    restore = subprocess.run(
        psql_base, input=sql_dump, capture_output=True, env=env, timeout=120,
    )
    if restore.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Restore failed: {restore.stderr.decode()}")

    storage = Path(settings.storage_path)
    for name in zf.namelist():
        if name.startswith("storage/") and not name.endswith("/"):
            rel = name[len("storage/"):]
            target = storage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))

    zf.close()

    await engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(lambda c: User.__table__.create(c, checkfirst=True))

    async with async_session_factory() as session:
        session.add(User(
            id=saved_user["id"],
            name=saved_user["name"],
            email=saved_user["email"],
            hashed_password=saved_user["hashed_password"],
            default_currency=saved_user["default_currency"],
            fiscal_year_start=saved_user["fiscal_year_start"],
        ))
        await session.commit()

    return {"status": "ok"}
