from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notifications import NotificationResponse, NotificationsListResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=NotificationsListResponse)
async def list_notifications(user: CurrentUser, db: DbDep) -> NotificationsListResponse:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.user_id)
        .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
    )
    notifications = result.scalars().all()
    unread = sum(1 for n in notifications if n.read_at is None)
    return NotificationsListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        unread_count=unread,
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: int, user: CurrentUser, db: DbDep) -> NotificationResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == user.user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOTIFICATION_NOT_FOUND", "message": f"Notification {notification_id} not found"},
        )
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(user: CurrentUser, db: DbDep) -> Response:
    now = datetime.now(tz=timezone.utc)
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.user_id, Notification.read_at.is_(None))
        .values(read_at=now)
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
