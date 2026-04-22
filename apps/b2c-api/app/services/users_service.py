import base64
import io
import json
import os
from pathlib import Path

import qrcode
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.users import (
    UpdateInterestsRequest,
    UpdateNotificationsRequest,
    UpdateProfileRequest,
    UserProfileResponse,
    UserResponse,
)

UPLOADS_DIR = Path("uploads/avatars")


def _generate_qr(user: User) -> str:
    data = json.dumps(
        {
            "user_id": user.user_id,
            "phone": user.phone,
            "name": user.name,
            "surname": user.surname,
        },
        ensure_ascii=False,
    )
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        phone=user.phone,
        name=user.name,
        surname=user.surname,
        organization=user.organization,
        avatar_url=user.avatar_url,
        interests=user.interests or [],
        push_enabled=user.push_enabled,
    )


class UsersService:
    def build_profile(self, user: User) -> UserProfileResponse:
        base = _to_response(user)
        return UserProfileResponse(**base.model_dump(), qr_code=_generate_qr(user))

    async def update_profile(
        self, user: User, data: UpdateProfileRequest, db: AsyncSession
    ) -> UserResponse:
        if data.name is not None:
            user.name = data.name
        if data.surname is not None:
            user.surname = data.surname
        if data.organization is not None:
            user.organization = data.organization
        await db.commit()
        await db.refresh(user)
        return _to_response(user)

    async def update_interests(
        self, user: User, data: UpdateInterestsRequest, db: AsyncSession
    ) -> UserResponse:
        user.interests = data.interests
        await db.commit()
        await db.refresh(user)
        return _to_response(user)

    async def update_avatar(
        self, user: User, file: UploadFile, db: AsyncSession
    ) -> UserResponse:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename or "avatar.jpg").suffix or ".jpg"
        filename = f"{user.user_id}{ext}"
        dest = UPLOADS_DIR / filename
        contents = await file.read()
        dest.write_bytes(contents)
        user.avatar_url = f"/uploads/avatars/{filename}"
        await db.commit()
        await db.refresh(user)
        return _to_response(user)

    async def update_notifications(
        self, user: User, data: UpdateNotificationsRequest, db: AsyncSession
    ) -> UserResponse:
        user.push_enabled = data.push_enabled
        await db.commit()
        await db.refresh(user)
        return _to_response(user)


users_service = UsersService()
