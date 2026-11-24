# Why: Pydantic schemas for booking creation, rescheduling, and response payloads.

from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from app.schemas.service import ServiceOut
from app.schemas.stylist import StylistSimpleOut


class BookingCreate(BaseModel):
    service_id: int = Field(..., description="ID of service to book")
    stylist_id: int = Field(..., description="ID of stylist performing service")
    start_ts: datetime = Field(..., description="Appointment start timestamp in UTC")
    hold_id: int | None = Field(default=None, description="Optional active pre-booking hold ID to convert")
    notes: str | None = Field(default=None, max_length=500, description="Optional customer notes")


class BookingReschedule(BaseModel):
    new_start_ts: datetime = Field(..., description="New appointment start timestamp in UTC")
    notes: str | None = Field(default=None, max_length=500, description="Optional updated notes")


class BookingOut(BaseModel):
    id: int
    user_id: int
    service_id: int
    stylist_id: int
    start_ts: datetime
    end_ts: datetime
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    service: ServiceOut | None = None
    stylist: StylistSimpleOut | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_ts", "end_ts", when_used="json")
    def serialize_utc_dt(self, dt: datetime) -> str:
        """Guarantees UTC timezone suffix (+00:00 or Z) in JSON output."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
