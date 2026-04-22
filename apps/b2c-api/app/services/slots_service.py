from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.slot import Slot
from app.models.talk import Talk
from app.models.user import User
from app.models.user_slot_selection import UserSlotSelection
from app.schemas.slots import SelectTalkRequest, TalkResponse, TalksListResponse


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": code, "message": message},
    )


def _talk_to_response(talk: Talk, selected_talk_id: int | None) -> TalkResponse:
    return TalkResponse(
        talk_id=talk.talk_id,
        slot_id=talk.slot_id,
        title=talk.title,
        speakers=talk.speakers or [],
        description=talk.description,
        is_selected=talk.talk_id == selected_talk_id,
    )


class SlotsService:
    async def _get_event(self, event_id: int, db: AsyncSession) -> Event:
        result = await db.execute(select(Event).where(Event.event_id == event_id))
        event = result.scalar_one_or_none()
        if event is None:
            raise _not_found("EVENT_NOT_FOUND", f"Event {event_id} not found")
        return event

    async def _get_slot(self, slot_id: int, event_id: int, db: AsyncSession) -> Slot:
        result = await db.execute(select(Slot).where(Slot.slot_id == slot_id))
        slot = result.scalar_one_or_none()
        if slot is None or slot.event_id != event_id:
            raise _not_found("SLOT_NOT_FOUND", f"Slot {slot_id} not found in event {event_id}")
        return slot

    async def _get_selection(
        self, user_id: int, slot_id: int, db: AsyncSession
    ) -> UserSlotSelection | None:
        result = await db.execute(
            select(UserSlotSelection).where(
                UserSlotSelection.user_id == user_id,
                UserSlotSelection.slot_id == slot_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_talks(
        self, event_id: int, slot_id: int, user: User, db: AsyncSession
    ) -> TalksListResponse:
        await self._get_event(event_id, db)
        await self._get_slot(slot_id, event_id, db)

        talks_result = await db.execute(select(Talk).where(Talk.slot_id == slot_id))
        talks = talks_result.scalars().all()

        selection = await self._get_selection(user.user_id, slot_id, db)
        selected_talk_id = selection.talk_id if selection else None

        return TalksListResponse(
            talks=[_talk_to_response(t, selected_talk_id) for t in talks],
            selected_talk_id=selected_talk_id,
        )

    async def select_talk(
        self, event_id: int, slot_id: int, data: SelectTalkRequest, user: User, db: AsyncSession
    ) -> TalkResponse:
        await self._get_event(event_id, db)
        await self._get_slot(slot_id, event_id, db)

        talk_result = await db.execute(select(Talk).where(Talk.talk_id == data.talk_id))
        talk = talk_result.scalar_one_or_none()
        if talk is None or talk.slot_id != slot_id:
            raise _not_found("TALK_NOT_FOUND", f"Talk {data.talk_id} not found in slot {slot_id}")

        # delete existing selection for this slot (if any), then insert new one
        await db.execute(
            delete(UserSlotSelection).where(
                UserSlotSelection.user_id == user.user_id,
                UserSlotSelection.slot_id == slot_id,
            )
        )
        db.add(UserSlotSelection(user_id=user.user_id, slot_id=slot_id, talk_id=data.talk_id))
        await db.commit()

        return _talk_to_response(talk, data.talk_id)

    async def deselect_talk(
        self, event_id: int, slot_id: int, user: User, db: AsyncSession
    ) -> None:
        await self._get_event(event_id, db)
        await self._get_slot(slot_id, event_id, db)

        selection = await self._get_selection(user.user_id, slot_id, db)
        if selection is None:
            raise _not_found("SELECTION_NOT_FOUND", "No talk selected for this slot")

        await db.delete(selection)
        await db.commit()


slots_service = SlotsService()
