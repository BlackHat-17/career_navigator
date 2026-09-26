"""
UserService
───────────
Handles user creation and retrieval.  Pure DB operations, no external calls.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.user import UserCreate

logger = get_logger(__name__)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_user(self, payload: UserCreate) -> User:
        # Enforce unique email
        existing = await self._db.scalar(
            select(User).where(User.email == payload.email)
        )
        if existing:
            raise ConflictError(
                f"A user with email '{payload.email}' already exists."
            )

        user = User(
            name=payload.name,
            email=payload.email,
            career_goal=payload.career_goal,
        )
        self._db.add(user)
        await self._db.flush()   # get the generated id without committing
        logger.info("Created user id=%s email=%s", user.id, user.email)
        return user

    async def get_user(self, user_id: UUID) -> User:
        user = await self._db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        return user
