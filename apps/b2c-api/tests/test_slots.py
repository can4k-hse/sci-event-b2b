from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.otp_code import OtpCode
from app.models.slot import Slot
from app.models.talk import Talk
from app.models.user import User
from app.models.user_slot_selection import UserSlotSelection

PHONE = "+79161234567"


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


async def _create_event(db: AsyncSession, title: str = "Test Event") -> Event:
    event = Event(title=title, published=True)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _create_slot(db: AsyncSession, event_id: int) -> Slot:
    slot = Slot(
        event_id=event_id,
        starts_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


async def _create_talk(db: AsyncSession, slot_id: int, title: str = "Talk") -> Talk:
    talk = Talk(slot_id=slot_id, title=title, speakers=["Alice Smith", "Bob Jones"])
    db.add(talk)
    await db.commit()
    await db.refresh(talk)
    return talk


# ── GET /v1/events/{event_id}/slots/{slot_id}/talks ───────────────────────────

async def test_get_talks_empty(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)

    r = await client.get(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/talks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["talks"] == []
    assert body["selected_talk_id"] is None


async def test_get_talks_lists_all(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    talk1 = await _create_talk(db, slot.slot_id, "Talk A")
    talk2 = await _create_talk(db, slot.slot_id, "Talk B")

    r = await client.get(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/talks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    talk_ids = {t["talk_id"] for t in r.json()["talks"]}
    assert talk_ids == {talk1.talk_id, talk2.talk_id}
    assert all(not t["is_selected"] for t in r.json()["talks"])


async def test_get_talks_with_selection(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    talk = await _create_talk(db, slot.slot_id, "Selected Talk")

    db.add(UserSlotSelection(user_id=user.user_id, slot_id=slot.slot_id, talk_id=talk.talk_id))
    await db.commit()

    r = await client.get(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/talks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["selected_talk_id"] == talk.talk_id
    assert body["talks"][0]["is_selected"] is True


async def test_get_talks_event_not_found(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    r = await client.get(
        "/v1/events/9999/slots/1/talks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "EVENT_NOT_FOUND"


async def test_get_talks_slot_not_in_event(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    event1 = await _create_event(db, "Event 1")
    event2 = await _create_event(db, "Event 2")
    slot_of_event2 = await _create_slot(db, event2.event_id)

    r = await client.get(
        f"/v1/events/{event1.event_id}/slots/{slot_of_event2.slot_id}/talks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "SLOT_NOT_FOUND"


async def test_get_talks_unauthorized(client: AsyncClient, db: AsyncSession) -> None:
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    r = await client.get(f"/v1/events/{event.event_id}/slots/{slot.slot_id}/talks")
    assert r.status_code == 401


# ── POST /v1/events/{event_id}/slots/{slot_id}/select ─────────────────────────

async def test_select_talk_success(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    talk = await _create_talk(db, slot.slot_id, "Great Talk")

    r = await client.post(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select",
        json={"talk_id": talk.talk_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["talk_id"] == talk.talk_id
    assert body["is_selected"] is True

    sel = await db.execute(
        select(UserSlotSelection).where(
            UserSlotSelection.user_id == user.user_id,
            UserSlotSelection.slot_id == slot.slot_id,
        )
    )
    assert sel.scalar_one().talk_id == talk.talk_id


async def test_select_talk_replaces_existing(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    talk1 = await _create_talk(db, slot.slot_id, "Talk 1")
    talk2 = await _create_talk(db, slot.slot_id, "Talk 2")

    await client.post(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select",
        json={"talk_id": talk1.talk_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select",
        json={"talk_id": talk2.talk_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["talk_id"] == talk2.talk_id

    result = await db.execute(
        select(UserSlotSelection).where(
            UserSlotSelection.user_id == user.user_id,
            UserSlotSelection.slot_id == slot.slot_id,
        )
    )
    assert result.scalar_one().talk_id == talk2.talk_id


async def test_select_talk_not_in_slot(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    event = await _create_event(db)
    slot1 = await _create_slot(db, event.event_id)
    slot2 = await _create_slot(db, event.event_id)
    talk_in_slot2 = await _create_talk(db, slot2.slot_id, "Wrong Slot Talk")

    r = await client.post(
        f"/v1/events/{event.event_id}/slots/{slot1.slot_id}/select",
        json={"talk_id": talk_in_slot2.talk_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TALK_NOT_FOUND"


async def test_select_talk_unauthorized(client: AsyncClient, db: AsyncSession) -> None:
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    r = await client.post(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select",
        json={"talk_id": 1},
    )
    assert r.status_code == 401


# ── DELETE /v1/events/{event_id}/slots/{slot_id}/select ───────────────────────

async def test_deselect_success(client: AsyncClient, db: AsyncSession) -> None:
    token, user = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    talk = await _create_talk(db, slot.slot_id)

    db.add(UserSlotSelection(user_id=user.user_id, slot_id=slot.slot_id, talk_id=talk.talk_id))
    await db.commit()

    r = await client.delete(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204

    result = await db.execute(
        select(UserSlotSelection).where(
            UserSlotSelection.user_id == user.user_id,
            UserSlotSelection.slot_id == slot.slot_id,
        )
    )
    assert result.scalar_one_or_none() is None


async def test_deselect_not_found(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await _auth(client, db)
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)

    r = await client.delete(
        f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "SELECTION_NOT_FOUND"


async def test_deselect_unauthorized(client: AsyncClient, db: AsyncSession) -> None:
    event = await _create_event(db)
    slot = await _create_slot(db, event.event_id)
    r = await client.delete(f"/v1/events/{event.event_id}/slots/{slot.slot_id}/select")
    assert r.status_code == 401
