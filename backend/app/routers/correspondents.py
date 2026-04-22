import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.correspondent import Correspondent
from app.schemas.correspondent import CorrespondentCreate, CorrespondentResponse, CorrespondentUpdate
from app.utils import slugify

router = APIRouter(prefix="/correspondents", tags=["correspondents"])


@router.get("", response_model=list[CorrespondentResponse])
async def list_correspondents(session: AsyncSession = Depends(get_session)) -> list[Correspondent]:
    result = await session.execute(select(Correspondent).order_by(Correspondent.name))
    return list(result.scalars().all())


@router.post("", response_model=CorrespondentResponse, status_code=201)
async def create_correspondent(
    data: CorrespondentCreate, session: AsyncSession = Depends(get_session)
) -> Correspondent:
    obj = Correspondent(
        name=data.name,
        slug=data.slug or slugify(data.name),
        notes=data.notes,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A correspondent with this name or slug already exists")
    await session.refresh(obj)
    return obj


@router.get("/{id}", response_model=CorrespondentResponse)
async def get_correspondent(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Correspondent:
    obj = await session.get(Correspondent, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Correspondent not found")
    return obj


@router.patch("/{id}", response_model=CorrespondentResponse)
async def update_correspondent(
    id: uuid.UUID, data: CorrespondentUpdate, session: AsyncSession = Depends(get_session)
) -> Correspondent:
    obj = await session.get(Correspondent, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Correspondent not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A correspondent with this slug already exists")
    await session.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
async def delete_correspondent(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    obj = await session.get(Correspondent, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Correspondent not found")
    await session.delete(obj)
    await session.commit()
