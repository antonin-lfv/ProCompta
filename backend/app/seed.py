from sqlalchemy import select

from app.database import async_session_factory
from app.models.document_type import DocumentType
from app.models.tag import Tag


async def seed_defaults() -> None:
    async with async_session_factory() as session:
        if not await session.scalar(select(DocumentType)):
            session.add_all([
                DocumentType(name="Facture",             slug="facture",             color="#6366f1"),
                DocumentType(name="Devis",               slug="devis",               color="#8b5cf6"),
                DocumentType(name="Contrat",             slug="contrat",             color="#ec4899"),
                DocumentType(name="Bon de commande",     slug="bon-de-commande",     color="#f97316"),
                DocumentType(name="Relevé",              slug="releve",              color="#06b6d4"),
                DocumentType(name="Reçu",                slug="recu",                color="#10b981"),
                DocumentType(name="Bulletin de salaire", slug="bulletin-de-salaire", color="#84cc16"),
                DocumentType(name="Rapport",             slug="rapport",             color="#64748b"),
                DocumentType(name="Avenant",             slug="avenant",             color="#f59e0b"),
                DocumentType(name="Attestation",         slug="attestation",         color="#14b8a6"),
                DocumentType(name="Avoir",               slug="avoir",               color="#a855f7"),
                DocumentType(name="Bordereau",           slug="bordereau",           color="#78716c"),
            ])
        if not await session.scalar(select(Tag)):
            session.add_all([
                Tag(name="Urgent",      slug="urgent",      color="#ef4444"),
                Tag(name="À payer",     slug="a-payer",     color="#f97316"),
                Tag(name="Payé",        slug="paye",        color="#10b981"),
                Tag(name="À vérifier", slug="a-verifier",  color="#eab308"),
                Tag(name="Important",   slug="important",   color="#6366f1"),
            ])
        await session.commit()
