"""
POST /api/v1/users    – create a user
GET  /api/v1/users/{user_id} – fetch a user
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    svc = UserService(db)
    user = await svc.create_user(payload)
    return UserRead.model_validate(user)


@router.get(
    "/by-email",
    response_model=UserRead,
    summary="Get a user by email",
)
async def get_user_by_email(
    email: str = Query(..., description="Email address of the user"),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    svc = UserService(db)
    user = await svc.get_user_by_email(email)
    return UserRead.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by ID",
)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    svc = UserService(db)
    user = await svc.get_user(user_id)
    return UserRead.model_validate(user)
