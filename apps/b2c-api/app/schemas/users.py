from typing import Any

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    user_id: int
    phone: str
    name: str | None
    surname: str | None
    organization: str | None
    avatar_url: str | None
    interests: list[Any]
    push_enabled: bool

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    qr_code: str  # base64-encoded PNG


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, max_length=100)
    surname: str | None = Field(None, max_length=100)
    organization: str | None = Field(None, max_length=255)


class UpdateInterestsRequest(BaseModel):
    interests: list[str]


class UpdateNotificationsRequest(BaseModel):
    push_enabled: bool
