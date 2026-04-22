from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.users import (
    UpdateInterestsRequest,
    UpdateNotificationsRequest,
    UpdateProfileRequest,
    UserProfileResponse,
    UserResponse,
)
from app.services.users_service import users_service

router = APIRouter(prefix="/users", tags=["users"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: CurrentUser) -> UserProfileResponse:
    return users_service.build_profile(user)


@router.patch("/me", response_model=UserResponse)
async def patch_me(user: CurrentUser, data: UpdateProfileRequest, db: DbDep) -> UserResponse:
    return await users_service.update_profile(user, data, db)


@router.patch("/me/interests", response_model=UserResponse)
async def patch_interests(
    user: CurrentUser, data: UpdateInterestsRequest, db: DbDep
) -> UserResponse:
    return await users_service.update_interests(user, data, db)


@router.patch("/me/avatar", response_model=UserResponse)
async def patch_avatar(user: CurrentUser, file: UploadFile, db: DbDep) -> UserResponse:
    return await users_service.update_avatar(user, file, db)


@router.patch("/me/notifications-settings", response_model=UserResponse)
async def patch_notifications(
    user: CurrentUser, data: UpdateNotificationsRequest, db: DbDep
) -> UserResponse:
    return await users_service.update_notifications(user, data, db)
