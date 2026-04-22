from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp_code import OtpCode
from app.models.user import User

PHONE = "+79161234567"


async def _send_and_get_code(client: AsyncClient, db: AsyncSession, phone: str = PHONE) -> str:
    """Отправляет OTP и возвращает код из БД."""
    await client.post("/v1/auth/send-code", json={"phone": phone})
    result = await db.execute(
        select(OtpCode)
        .where(OtpCode.phone == phone)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    return result.scalar_one().code


# ── POST /v1/auth/send-code ──────────────────────────────────────────────────

async def test_send_code_success(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/send-code", json={"phone": PHONE})
    assert r.status_code == 200
    assert r.json() == {"message": "Code sent successfully"}


async def test_send_code_invalid_phone(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/send-code", json={"phone": "not-a-phone"})
    assert r.status_code == 422


async def test_send_code_rate_limit(client: AsyncClient, db: AsyncSession) -> None:
    from app.config import get_settings
    limit = get_settings().otp_rate_limit_count
    for _ in range(limit):
        await client.post("/v1/auth/send-code", json={"phone": PHONE})
    r = await client.post("/v1/auth/send-code", json={"phone": PHONE})
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "RATE_LIMITED"


# ── POST /v1/auth/verify-code ────────────────────────────────────────────────

async def test_verify_code_creates_user(client: AsyncClient, db: AsyncSession) -> None:
    code = await _send_and_get_code(client, db)
    r = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["expires_in"] > 0

    result = await db.execute(select(User).where(User.phone == PHONE))
    assert result.scalar_one_or_none() is not None


async def test_verify_code_existing_user_same_id(client: AsyncClient, db: AsyncSession) -> None:
    from app.utils.jwt import decode_access_token

    code = await _send_and_get_code(client, db)
    r1 = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code})
    user_id_1 = decode_access_token(r1.json()["access_token"])["sub"]

    code2 = await _send_and_get_code(client, db)
    r2 = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code2})
    assert r2.status_code == 200
    user_id_2 = decode_access_token(r2.json()["access_token"])["sub"]

    assert user_id_1 == user_id_2

    result = await db.execute(select(User).where(User.phone == PHONE))
    users = result.scalars().all()
    assert len(users) == 1


async def test_verify_code_invalid_code(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": "000000"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CODE"


async def test_verify_code_wrong_length(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": "1234"})
    assert r.status_code == 422


async def test_verify_code_expired_otp(client: AsyncClient, db: AsyncSession) -> None:
    expired_otp = OtpCode(
        phone=PHONE,
        code="123456",
        expires_at=datetime.now(tz=timezone.utc) - timedelta(minutes=1),
    )
    db.add(expired_otp)
    await db.commit()

    r = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": "123456"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CODE"


# ── POST /v1/auth/refresh ────────────────────────────────────────────────────

async def test_refresh_token_success(client: AsyncClient, db: AsyncSession) -> None:
    code = await _send_and_get_code(client, db)
    tokens = (await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code})).json()

    r = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_refresh_token_invalid(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/refresh", json={"refresh_token": "invalid-token"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "REFRESH_INVALID"


async def test_refresh_token_after_logout(client: AsyncClient, db: AsyncSession) -> None:
    code = await _send_and_get_code(client, db)
    tokens = (await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code})).json()

    await client.post(
        "/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    r = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "REFRESH_INVALID"


# ── POST /v1/auth/logout ─────────────────────────────────────────────────────

async def test_logout_success(client: AsyncClient, db: AsyncSession) -> None:
    code = await _send_and_get_code(client, db)
    tokens = (await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code})).json()

    r = await client.post(
        "/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 204


async def test_logout_without_token(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/logout", json={"refresh_token": "any"})
    assert r.status_code == 401
