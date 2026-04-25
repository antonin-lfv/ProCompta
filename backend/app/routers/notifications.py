import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread-count")
async def unread_count(session: AsyncSession = Depends(get_session)) -> dict:
    count = await session.scalar(
        select(func.count(Notification.id)).where(Notification.read == False)
    )
    return {"count": count or 0}


@router.patch("/read-all")
async def mark_all_read(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(Notification).where(Notification.read == False)
    )
    notifs = list(result.scalars().all())
    for n in notifs:
        n.read = True
    await session.commit()
    return {"updated": len(notifs)}


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    read: bool | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[Notification]:
    stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    if read is not None:
        stmt = stmt.where(Notification.read == read)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{id}/read", response_model=NotificationResponse)
async def mark_read(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Notification:
    notif = await session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.read = True
    await session.commit()
    return notif


@router.patch("/{id}/unread", response_model=NotificationResponse)
async def mark_unread(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Notification:
    notif = await session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.read = False
    await session.commit()
    return notif


@router.delete("/{id}", status_code=204)
async def delete_notification(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    notif = await session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    await session.delete(notif)
    await session.commit()
