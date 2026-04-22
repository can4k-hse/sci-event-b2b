from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.talk import Talk
from app.models.user import User
from app.schemas.slots import TalkDetailResponse

router = APIRouter(prefix="/talks", tags=["talks"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{talk_id}", response_model=TalkDetailResponse)
async def get_talk(talk_id: int, _user: CurrentUser, db: DbDep) -> TalkDetailResponse:
    result = await db.execute(select(Talk).where(Talk.talk_id == talk_id))
    talk = result.scalar_one_or_none()
    if talk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TALK_NOT_FOUND", "message": f"Talk {talk_id} not found"},
        )
    return TalkDetailResponse(
        talk_id=talk.talk_id,
        slot_id=talk.slot_id,
        title=talk.title,
        speakers=talk.speakers or [],
        description=talk.description,
    )
