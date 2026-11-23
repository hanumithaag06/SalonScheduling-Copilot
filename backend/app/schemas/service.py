# Why: Pydantic schemas for salon services.
# Enforces non-negative prices and positive service durations (>0).

from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    duration_min: int = Field(..., gt=0, description="Service duration in minutes must be > 0")
    price: Decimal = Field(..., ge=0, description="Price must be non-negative (>= 0)")
    is_active: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    duration_min: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ServiceOut(ServiceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
