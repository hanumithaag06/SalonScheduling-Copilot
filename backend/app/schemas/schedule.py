# Why: Pydantic schemas for stylist weekly schedules and time-off/holidays.
# Validates that end times are strictly after start times.

from datetime import datetime, time
from pydantic import BaseModel, Field, ConfigDict, model_validator


class WorkingHoursCreate(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time")
        return self


class WorkingHoursOut(BaseModel):
    id: int
    stylist_id: int
    weekday: int
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class TimeOffCreate(BaseModel):
    start_ts: datetime = Field(..., description="Start timestamp in UTC")
    end_ts: datetime = Field(..., description="End timestamp in UTC")
    reason: str = Field(..., min_length=2, max_length=255)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be strictly after start_ts")
        return self


class TimeOffOut(BaseModel):
    id: int
    stylist_id: int
    start_ts: datetime
    end_ts: datetime
    reason: str

    model_config = ConfigDict(from_attributes=True)
