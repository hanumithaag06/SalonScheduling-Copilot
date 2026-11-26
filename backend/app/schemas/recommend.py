# Why: Pydantic schemas for explainable appointment recommendation responses.
# Serializes multi-factor recommendation scores, breakdown, and natural language reasons.

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdownOut(BaseModel):
    """Detailed score contribution per recommendation factor."""
    past_bookings: float = Field(..., description="Loyalty bonus for past visits (+3 max)")
    preferred_time: float = Field(..., description="Time window preference bonus (+2)")
    specialization: float = Field(..., description="Stylist expertise match bonus (+1)")
    adjacent_booking: float = Field(..., description="Schedule gap minimization bonus (+1)")


class RecommendationOut(BaseModel):
    """An explainable appointment recommendation returned to the customer."""
    service_id: int | None = Field(default=None, description="Salon service ID")
    stylist_id: int
    stylist_name: str
    stylist_specialization: str
    start_ts: datetime
    end_ts: datetime
    duration_min: int
    price: Decimal
    score: float = Field(..., description="Composite recommendation score")
    score_breakdown: ScoreBreakdownOut
    reason: str = Field(..., description="Human-readable justification for this recommendation")

    model_config = ConfigDict(from_attributes=True)

