# Why: Pydantic schemas for notification delivery and in-app alerts.

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: int
    user_id: int
    booking_id: int | None
    type: str
    message: str
    channel: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

