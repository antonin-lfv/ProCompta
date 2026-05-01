from app.models.document import CategoryEnum, Document
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.notification import Notification, NotificationTypeEnum


def is_complete(doc: Document) -> bool:
    return bool(
        doc.document_type_id
        and doc.correspondent_id
        and (doc.category == CategoryEnum.autre or doc.amount_ttc)
    )


def missing_body(doc: Document) -> str:
    missing = []
    if not doc.correspondent_id:
        missing.append("correspondant")
    if not doc.document_type_id:
        missing.append("type")
    if doc.category != CategoryEnum.autre and not doc.amount_ttc:
        missing.append("montant")
    return "Sans " + " · sans ".join(missing) if missing else "Informations incomplètes"


async def sync_notification(doc: Document, session: AsyncSession) -> None:
    unread_result = await session.execute(
        select(Notification).where(Notification.document_id == doc.id, Notification.read == False)
    )
    unread = list(unread_result.scalars().all())

    if is_complete(doc):
        for n in unread:
            n.read = True
    else:
        if not unread:
            existing = await session.scalar(
                select(Notification)
                .where(Notification.document_id == doc.id)
                .order_by(Notification.created_at.desc())
                .limit(1)
            )
            if existing:
                existing.read = False
                existing.title = f"« {doc.title} » - informations manquantes"
                existing.body = missing_body(doc)
            else:
                session.add(Notification(
                    type=NotificationTypeEnum.incomplete_document,
                    document_id=doc.id,
                    title=f"« {doc.title} » - informations manquantes",
                    body=missing_body(doc),
                ))
    await session.commit()
