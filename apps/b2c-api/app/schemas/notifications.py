from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    notification_id: int
    text: str
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
