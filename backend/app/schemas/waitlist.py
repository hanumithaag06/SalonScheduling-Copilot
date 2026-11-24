# Why: Pydantic schemas for salon appointment waitlist requests and offers.

from datetime import date as date_type, datetime
from pydantic import BaseModel, ConfigDict, Field


class WaitlistCreate(BaseModel):
    service_id: int = Field(..., description="ID of the desired salon service")
    stylist_id: int | None = Field(default=None, description="Optional stylist preference (None = any stylist)")
    date: date_type = Field(..., description="Desired appointment date (YYYY-MM-DD)")
    time_pref: str = Field(
        default="any",
        description="Time preference: 'morning', 'afternoon', 'evening', or 'any'",
    )


class WaitlistOut(BaseModel):
    id: int
    user_id: int
    service_id: int
    stylist_id: int | None
    date: date_type
    time_pref: str
    status: str
    offered_slot_start: datetime | None
    offer_expires_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

