import base64
import io

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp_code import OtpCode
from app.models.user import User

PHONE = "+79161234567"


async def _auth(client: AsyncClient, db: AsyncSession, phone: str = PHONE) -> tuple[str, User]:
    """Creates/retrieves a user via OTP flow, returns (access_token, user)."""
    await client.post("/v1/auth/send-code", json={"phone": phone})
    result = await db.execute(
        select(OtpCode)
        .where(OtpCode.phone == phone)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    code = result.scalar_one().code
    r = await client.post("/v1/auth/verify-code", json={"phone": phone, "code": code})
    access_token = r.json()["access_token"]
    user_result = await db.execute(select(User).where(User.phone == phone))
    return access_token, user_result.scalar_one()


# ── GET /v1/users/me ──────────────────────────────────────────────────────────

async def test_get_me_success(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    r = await client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user.user_id
    assert body["phone"] == PHONE
    assert "qr_code" in body
    # qr_code must be valid base64 PNG
    raw = base64.b64decode(body["qr_code"])
    assert raw[:4] == b"\x89PNG"


async def test_get_me_unauthorized(client: AsyncClient) -> None:
    r = await client.get("/v1/users/me")
    assert r.status_code == 401


# ── PATCH /v1/users/me ────────────────────────────────────────────────────────

async def test_patch_me_success(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me",
        json={"name": "Ivan", "surname": "Petrov", "organization": "MIPT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Ivan"
    assert body["surname"] == "Petrov"
    assert body["organization"] == "MIPT"


async def test_patch_me_partial(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me",
        json={"name": "Partial"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Partial"
    assert body["surname"] is None


async def test_patch_me_unauthorized(client: AsyncClient) -> None:
    r = await client.patch("/v1/users/me", json={"name": "X"})
    assert r.status_code == 401


async def test_patch_me_name_too_long(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me",
        json={"name": "A" * 101},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ── PATCH /v1/users/me/interests ──────────────────────────────────────────────

async def test_patch_interests_success(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me/interests",
        json={"interests": ["AI", "robotics", "space"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["interests"] == ["AI", "robotics", "space"]


async def test_patch_interests_empty(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me/interests",
        json={"interests": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["interests"] == []


async def test_patch_interests_invalid(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me/interests",
        json={"interests": "not-a-list"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ── PATCH /v1/users/me/avatar ─────────────────────────────────────────────────

def _minimal_jpeg() -> bytes:
    """Returns a minimal valid JPEG."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
        b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
        b"\x1c $.' \",#\x1c\x1c(7),\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00"
        b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        b"\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00"
        b"\xfb\x00\x00\xff\xd9"
    )


async def test_patch_avatar_success(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    jpeg = _minimal_jpeg()
    r = await client.patch(
        "/v1/users/me/avatar",
        files={"file": ("photo.jpg", io.BytesIO(jpeg), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["avatar_url"] is not None
    assert str(user.user_id) in body["avatar_url"]


async def test_patch_avatar_unauthorized(client: AsyncClient) -> None:
    jpeg = _minimal_jpeg()
    r = await client.patch(
        "/v1/users/me/avatar",
        files={"file": ("photo.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert r.status_code == 401


# ── PATCH /v1/users/me/notifications-settings ─────────────────────────────────

async def test_patch_notifications_disable(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.patch(
        "/v1/users/me/notifications-settings",
        json={"push_enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["push_enabled"] is False


async def test_patch_notifications_enable(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    # disable first, then enable
    await client.patch(
        "/v1/users/me/notifications-settings",
        json={"push_enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.patch(
        "/v1/users/me/notifications-settings",
        json={"push_enabled": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["push_enabled"] is True


async def test_patch_notifications_invalid(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    # list is not coercible to bool
    r = await client.patch(
        "/v1/users/me/notifications-settings",
        json={"push_enabled": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
