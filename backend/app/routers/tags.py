import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagResponse, TagUpdate
from app.utils import slugify

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(session: AsyncSession = Depends(get_session)) -> list[Tag]:
    result = await session.execute(select(Tag).order_by(Tag.name))
    return list(result.scalars().all())


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(data: TagCreate, session: AsyncSession = Depends(get_session)) -> Tag:
    obj = Tag(name=data.name, slug=data.slug or slugify(data.name), color=data.color)
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A tag with this name or slug already exists")
    await session.refresh(obj)
    return obj


@router.get("/{id}", response_model=TagResponse)
async def get_tag(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Tag:
    obj = await session.get(Tag, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tag not found")
    return obj


@router.patch("/{id}", response_model=TagResponse)
async def update_tag(
    id: uuid.UUID, data: TagUpdate, session: AsyncSession = Depends(get_session)
) -> Tag:
    obj = await session.get(Tag, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tag not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A tag with this slug already exists")
    await session.refresh(obj)
    return obj


@router.delete("/{id}", status_code=204)
async def delete_tag(id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    obj = await session.get(Tag, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tag not found")
    await session.delete(obj)
    await session.commit()
