import asyncio
import logging
import uuid
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.notification import Notification, NotificationTypeEnum
from app.models.reminder import Reminder

router = APIRouter(tags=["reminders"])


class ReminderCreate(BaseModel):
    name: str
    description: str | None = None
    frequency_days: int
    next_due_date: date
    notify_email: bool = True
    notify_inapp: bool = True
    active: bool = True


class ReminderUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    frequency_days: int | None = None
    next_due_date: date | None = None
    notify_email: bool | None = None
    notify_inapp: bool | None = None
    active: bool | None = None


class ReminderResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    frequency_days: int
    next_due_date: date
    notify_email: bool
    notify_inapp: bool
    active: bool
    last_triggered_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/reminders", response_model=list[ReminderResponse])
async def list_reminders(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Reminder).order_by(Reminder.next_due_date))
    return result.scalars().all()


@router.post("/reminders", response_model=ReminderResponse, status_code=201)
async def create_reminder(body: ReminderCreate, session: AsyncSession = Depends(get_session)):
    reminder = Reminder(**body.model_dump())
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


@router.patch("/reminders/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdate,
    session: AsyncSession = Depends(get_session),
):
    reminder = await session.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    await session.commit()
    await session.refresh(reminder)
    return reminder


@router.delete("/reminders/{reminder_id}", status_code=204)
async def delete_reminder(reminder_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    reminder = await session.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404)
    await session.delete(reminder)
    await session.commit()


@router.post("/reminders/{reminder_id}/trigger")
async def trigger_reminder(reminder_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    reminder = await session.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404)
    await _fire_reminder(reminder, session, advance=False)
    return {"ok": True}


async def _fire_reminder(reminder: Reminder, session: AsyncSession, advance: bool = True) -> None:
    from app.config import settings
    from app.models.user import User
    from app.services.smtp_service import send_reminder_email

    if reminder.notify_inapp:
        notif = Notification(
            type=NotificationTypeEnum.reminder_due,
            title=f"Rappel : {reminder.name}",
            body=reminder.description or f"Échéance prévue le {reminder.next_due_date.isoformat()}",
        )
        session.add(notif)

    if reminder.notify_email and settings.smtp_configured:
        user = await session.scalar(select(User))
        to_email = user.email if user else None
        if not to_email:
            logger.warning("Reminder email skipped: no user found in database")
        elif not to_email.lower().endswith("@gmail.com") and settings.smtp_host == "smtp.gmail.com":
            logger.warning("Reminder email skipped: %s is not a Gmail address (smtp_host=smtp.gmail.com)", to_email)
        else:
            body_html = f"""
            <p>Bonjour,</p>
            <p>Rappel ProCompta : <strong>{reminder.name}</strong></p>
            {"<p>" + reminder.description + "</p>" if reminder.description else ""}
            <p>Échéance prévue : {reminder.next_due_date.isoformat()}</p>
            """
            await asyncio.to_thread(send_reminder_email, f"[ProCompta] Rappel : {reminder.name}", body_html, to_email)

    if advance:
        from datetime import timedelta
        reminder.last_triggered_at = datetime.now(timezone.utc)
        reminder.next_due_date = reminder.next_due_date + timedelta(days=reminder.frequency_days)
    await session.commit()
