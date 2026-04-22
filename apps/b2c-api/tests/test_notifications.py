from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.otp_code import OtpCode
from app.models.user import User

PHONE = "+79161234567"
OTHER_PHONE = "+79169999999"


async def _auth(client: AsyncClient, db: AsyncSession, phone: str = PHONE) -> tuple[str, User]:
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


async def _create_notification(
    db: AsyncSession, user_id: int, text: str = "Hello", read: bool = False
) -> Notification:
    n = Notification(
        user_id=user_id,
        text=text,
        read_at=datetime.now(tz=timezone.utc) if read else None,
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


# ── GET /v1/notifications ─────────────────────────────────────────────────────

async def test_list_notifications_empty(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.get("/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["notifications"] == []
    assert body["unread_count"] == 0


async def test_list_notifications_returns_own_only(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    _, other = await _auth(client, db, OTHER_PHONE)

    await _create_notification(db, user.user_id, "For me")
    await _create_notification(db, other.user_id, "For other")

    r = await client.get("/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["notifications"]) == 1
    assert body["notifications"][0]["text"] == "For me"


async def test_list_notifications_unread_count(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    await _create_notification(db, user.user_id, "Unread 1", read=False)
    await _create_notification(db, user.user_id, "Unread 2", read=False)
    await _create_notification(db, user.user_id, "Read", read=True)

    r = await client.get("/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["notifications"]) == 3
    assert body["unread_count"] == 2


async def test_list_notifications_ordered_newest_first(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    n1 = await _create_notification(db, user.user_id, "First")
    n2 = await _create_notification(db, user.user_id, "Second")

    r = await client.get("/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    ids = [n["notification_id"] for n in r.json()["notifications"]]
    assert ids == [n2.notification_id, n1.notification_id]


async def test_list_notifications_unauthorized(client: AsyncClient) -> None:
    r = await client.get("/v1/notifications")
    assert r.status_code == 401


# ── GET /v1/notifications/{notification_id} ───────────────────────────────────

async def test_get_notification_success(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    n = await _create_notification(db, user.user_id, "Important update")

    r = await client.get(
        f"/v1/notifications/{n.notification_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["notification_id"] == n.notification_id
    assert body["text"] == "Important update"
    assert body["read_at"] is None


async def test_get_notification_not_found(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.get(
        "/v1/notifications/9999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOTIFICATION_NOT_FOUND"


async def test_get_notification_other_user(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    _, other = await _auth(client, db, OTHER_PHONE)
    n = await _create_notification(db, other.user_id, "Not yours")

    r = await client.get(
        f"/v1/notifications/{n.notification_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_get_notification_unauthorized(client: AsyncClient) -> None:
    r = await client.get("/v1/notifications/1")
    assert r.status_code == 401


# ── POST /v1/notifications/read-all ──────────────────────────────────────────

async def test_read_all_success(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    await _create_notification(db, user.user_id, "A")
    await _create_notification(db, user.user_id, "B")

    r = await client.post("/v1/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204

    list_r = await client.get("/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    body = list_r.json()
    assert body["unread_count"] == 0
    assert all(n["read_at"] is not None for n in body["notifications"])


async def test_read_all_only_marks_own(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    _, other = await _auth(client, db, OTHER_PHONE)

    await _create_notification(db, user.user_id, "Mine")
    other_n = await _create_notification(db, other.user_id, "Others")

    await client.post("/v1/notifications/read-all", headers={"Authorization": f"Bearer {token}"})

    result = await db.execute(
        select(Notification).where(Notification.notification_id == other_n.notification_id)
    )
    assert result.scalar_one().read_at is None


async def test_read_all_empty_is_ok(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.post("/v1/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204


async def test_read_all_unauthorized(client: AsyncClient) -> None:
    r = await client.post("/v1/notifications/read-all")
    assert r.status_code == 401
