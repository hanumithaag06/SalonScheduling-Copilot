# Why: Pydantic schemas for AI booking assistant parsing and recommendation suggestions.
# Validates natural language inputs and serializes extracted slot recommendations with explanations.

from datetime import date as date_type
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recommend import RecommendationOut


class AssistantParseRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Customer natural language booking request")


class AssistantParseResponse(BaseModel):
    service: str | None = Field(default=None, description="Extracted salon service name")
    service_id: int | None = Field(default=None, description="Matched service database ID")
    date: date_type | None = Field(default=None, description="Target appointment date (YYYY-MM-DD)")
    time_pref: str | None = Field(default=None, description="Preferred time of day: morning, afternoon, evening, or HH:MM")
    max_price: Decimal | None = Field(default=None, description="Budget constraint or maximum price")
    missing_fields: list[str] = Field(default_factory=list, description="Mandatory fields needed to proceed")
    follow_up_question: str | None = Field(default=None, description="Clarifying question if information is incomplete")
    source: str = Field(default="keyword_fallback", description="Extraction backend: 'llm' or 'keyword_fallback'")

    model_config = ConfigDict(from_attributes=True)


class AssistantSuggestRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Customer conversational booking query")
    service_id: int | None = Field(default=None, description="Optional override service ID")
    date: date_type | None = Field(default=None, description="Optional override date")
    time_pref: str | None = Field(default=None, description="Optional override time preference")
    max_price: Decimal | None = Field(default=None, description="Optional override budget constraint")


class AssistantSuggestResponse(BaseModel):
    intent: AssistantParseResponse
    follow_up_question: str | None = Field(default=None, description="Clarifying question if fields are missing")
    suggestions: list[RecommendationOut] = Field(default_factory=list, description="Top recommended appointment slots with reasons")
    message: str = Field(..., description="Assistant reply message to customer")
    booking_instructions: str = Field(
        default="To confirm an appointment, submit your chosen slot to POST /bookings. The assistant never creates bookings directly.",
        description="Explicit notice that booking creation requires user confirmation",
    )

    model_config = ConfigDict(from_attributes=True)
