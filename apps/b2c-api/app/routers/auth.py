from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    MessageResponse,
    RefreshRequest,
    SendCodeRequest,
    TokenPairResponse,
    VerifyCodeRequest,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/send-code", response_model=MessageResponse)
async def send_code(body: SendCodeRequest, db: DbDep) -> MessageResponse:
    if await auth_service.check_rate_limit(db, body.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many OTP requests. Please wait before trying again.",
            },
        )
    await auth_service.create_otp(db, body.phone)
    return MessageResponse(message="Code sent successfully")


@router.post("/verify-code", response_model=TokenPairResponse)
async def verify_code(body: VerifyCodeRequest, db: DbDep) -> TokenPairResponse:
    valid = await auth_service.verify_otp(db, body.phone, body.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CODE",
                "message": "Code is invalid or has expired",
            },
        )
    user = await auth_service.find_or_create_user(db, body.phone)
    access_token, refresh_token, expires_in = await auth_service.create_token_pair(db, user)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest, db: DbDep) -> AccessTokenResponse:
    result = await auth_service.refresh_access_token(db, body.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "REFRESH_INVALID",
                "message": "Refresh token is invalid, expired, or revoked",
            },
        )
    access_token, expires_in = result
    return AccessTokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: DbDep, _current_user: CurrentUser) -> Response:
    await auth_service.revoke_refresh_token(db, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
