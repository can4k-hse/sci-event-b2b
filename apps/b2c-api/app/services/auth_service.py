import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.otp_code import OtpCode
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.sms_service import sms_service
from app.utils.jwt import create_access_token
from app.utils.security import generate_opaque_token, hash_token

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:

    async def check_rate_limit(self, db: AsyncSession, phone: str) -> bool:
        window_start = datetime.now(tz=timezone.utc) - timedelta(
            minutes=settings.otp_rate_limit_window_minutes
        )
        result = await db.execute(
            select(func.count(OtpCode.id)).where(
                OtpCode.phone == phone,
                OtpCode.created_at >= window_start,
            )
        )
        count = result.scalar_one()
        return count >= settings.otp_rate_limit_count

    async def create_otp(self, db: AsyncSession, phone: str) -> str:
        code = str(random.randint(100000, 999999))
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.otp_expire_minutes
        )
        otp = OtpCode(phone=phone, code=code, expires_at=expires_at)
        db.add(otp)
        await db.commit()
        await sms_service.send_otp(phone, code)
        return code

    async def verify_otp(self, db: AsyncSession, phone: str, code: str) -> bool:
        now = datetime.now(tz=timezone.utc)
        result = await db.execute(
            select(OtpCode)
            .where(
                OtpCode.phone == phone,
                OtpCode.code == code,
                OtpCode.used_at.is_(None),
                OtpCode.expires_at > now,
            )
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )
        otp = result.scalar_one_or_none()
        if otp is None:
            return False
        otp.used_at = now
        await db.commit()
        return True

    async def find_or_create_user(self, db: AsyncSession, phone: str) -> User:
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(phone=phone)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("New user created for phone %s (user_id=%s)", phone, user.user_id)
        return user

    async def create_token_pair(self, db: AsyncSession, user: User) -> tuple[str, str, int]:
        access_token, expires_in = create_access_token(subject=user.user_id)

        raw_refresh = generate_opaque_token()
        token_hash = hash_token(raw_refresh)
        refresh_expires = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        db_token = RefreshToken(
            user_id=user.user_id,
            token_hash=token_hash,
            expires_at=refresh_expires,
        )
        db.add(db_token)
        await db.commit()

        return access_token, raw_refresh, expires_in

    async def refresh_access_token(
        self, db: AsyncSession, raw_refresh: str
    ) -> tuple[str, int] | None:
        token_hash = hash_token(raw_refresh)
        now = datetime.now(tz=timezone.utc)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.expires_at > now,
                RefreshToken.revoked_at.is_(None),
            )
        )
        db_token = result.scalar_one_or_none()
        if db_token is None:
            return None

        access_token, expires_in = create_access_token(subject=db_token.user_id)
        return access_token, expires_in

    async def revoke_refresh_token(self, db: AsyncSession, raw_refresh: str) -> bool:
        token_hash = hash_token(raw_refresh)
        now = datetime.now(tz=timezone.utc)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        db_token = result.scalar_one_or_none()
        if db_token is None:
            return False

        db_token.revoked_at = now
        await db.commit()
        return True


auth_service = AuthService()
