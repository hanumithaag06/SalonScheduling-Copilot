# Why: Pydantic schemas for appointment slot availability queries and responses.

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class SlotOut(BaseModel):
    stylist_id: int
    stylist_name: str
    start_ts: datetime
    end_ts: datetime
    duration_min: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)

