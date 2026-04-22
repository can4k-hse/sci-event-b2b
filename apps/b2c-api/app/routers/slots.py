from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.slots import SelectTalkRequest, TalkResponse, TalksListResponse
from app.services.slots_service import slots_service

router = APIRouter(prefix="/events", tags=["slots"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{event_id}/slots/{slot_id}/talks", response_model=TalksListResponse)
async def get_talks(
    event_id: int, slot_id: int, user: CurrentUser, db: DbDep
) -> TalksListResponse:
    return await slots_service.get_talks(event_id, slot_id, user, db)


@router.post("/{event_id}/slots/{slot_id}/select", response_model=TalkResponse)
async def select_talk(
    event_id: int, slot_id: int, data: SelectTalkRequest, user: CurrentUser, db: DbDep
) -> TalkResponse:
    return await slots_service.select_talk(event_id, slot_id, data, user, db)


@router.delete("/{event_id}/slots/{slot_id}/select", status_code=status.HTTP_204_NO_CONTENT)
async def deselect_talk(
    event_id: int, slot_id: int, user: CurrentUser, db: DbDep
) -> Response:
    await slots_service.deselect_talk(event_id, slot_id, user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
