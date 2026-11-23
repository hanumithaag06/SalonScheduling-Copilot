# Why: Pydantic schemas for stylist management and service assignments.

from pydantic import BaseModel, Field, ConfigDict
from app.schemas.service import ServiceOut


class StylistBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    specialization: str = Field(..., min_length=2, max_length=100)
    is_active: bool = True


class StylistCreate(StylistBase):
    service_ids: list[int] = Field(default_factory=list, description="IDs of services this stylist can perform")


class StylistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    specialization: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None
    service_ids: list[int] | None = None


class StylistOut(StylistBase):
    id: int
    services: list[ServiceOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StylistServiceAssign(BaseModel):
    service_ids: list[int] = Field(..., description="Complete list of service IDs for this stylist")
