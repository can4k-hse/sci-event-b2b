from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.otp_code import OtpCode
from app.models.slot import Slot
from app.models.talk import Talk
from app.models.user import User

PHONE = "+79161234567"


async def _auth(client: AsyncClient, db: AsyncSession) -> str:
    await client.post("/v1/auth/send-code", json={"phone": PHONE})
    result = await db.execute(
        select(OtpCode)
        .where(OtpCode.phone == PHONE)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    code = result.scalar_one().code
    r = await client.post("/v1/auth/verify-code", json={"phone": PHONE, "code": code})
    return r.json()["access_token"]


async def _create_talk(db: AsyncSession) -> Talk:
    event = Event(title="Conf 2026", published=True)
    db.add(event)
    await db.flush()

    from datetime import datetime, timezone
    slot = Slot(
        event_id=event.event_id,
        starts_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
    )
    db.add(slot)
    await db.flush()

    talk = Talk(
        slot_id=slot.slot_id,
        title="Advances in Quantum ML",
        speakers=["Alice Smith", "Bob Jones"],
        description="A deep dive into quantum approaches.",
    )
    db.add(talk)
    await db.commit()
    await db.refresh(talk)
    return talk


# ── GET /v1/talks/{talk_id} ───────────────────────────────────────────────────

async def test_get_talk_success(client: AsyncClient, db: AsyncSession) -> None:
    token = await _auth(client, db)
    talk = await _create_talk(db)

    r = await client.get(
        f"/v1/talks/{talk.talk_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["talk_id"] == talk.talk_id
    assert body["slot_id"] == talk.slot_id
    assert body["title"] == "Advances in Quantum ML"
    assert body["speakers"] == ["Alice Smith", "Bob Jones"]
    assert body["description"] == "A deep dive into quantum approaches."
    assert "is_selected" not in body


async def test_get_talk_no_speakers(client: AsyncClient, db: AsyncSession) -> None:
    token = await _auth(client, db)

    event = Event(title="E", published=True)
    db.add(event)
    await db.flush()
    from datetime import datetime, timezone
    slot = Slot(event_id=event.event_id,
                starts_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc))
    db.add(slot)
    await db.flush()
    talk = Talk(slot_id=slot.slot_id, title="Solo Talk", speakers=[])
    db.add(talk)
    await db.commit()
    await db.refresh(talk)

    r = await client.get(
        f"/v1/talks/{talk.talk_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["speakers"] == []


async def test_get_talk_not_found(client: AsyncClient, db: AsyncSession) -> None:
    token = await _auth(client, db)
    r = await client.get("/v1/talks/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TALK_NOT_FOUND"


async def test_get_talk_unauthorized(client: AsyncClient) -> None:
    r = await client.get("/v1/talks/1")
    assert r.status_code == 401
