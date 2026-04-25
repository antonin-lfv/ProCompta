import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401)
    # Attach user to session so it's not detached
    return await session.merge(user)
