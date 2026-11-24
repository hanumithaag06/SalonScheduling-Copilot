# Why: Pydantic schemas for the 5-minute pre-booking slot hold mechanism.

from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class HoldCreate(BaseModel):
    service_id: int = Field(..., description="ID of service to determine slot duration")
    stylist_id: int = Field(..., description="ID of stylist to hold")
    start_ts: datetime = Field(..., description="Desired start timestamp in UTC")


class HoldOut(BaseModel):
    id: int
    user_id: int
    stylist_id: int
    start_ts: datetime
    end_ts: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_ts", "end_ts", "expires_at", when_used="json")
    def serialize_utc(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
