# Why: AI booking assistant router exposing POST /assistant/parse and POST /assistant/suggest.
# Parses natural language prompts into structured intent and offers ranked appointment slots.
# Enforces the core architecture rule: The assistant never creates bookings directly.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_optional_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.assistant import (
    AssistantParseRequest,
    AssistantParseResponse,
    AssistantSuggestRequest,
    AssistantSuggestResponse,
)
from app.services.assistant_service import (
    parse_assistant_message,
    suggest_assistant_slots,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/parse", response_model=AssistantParseResponse)
async def parse_prompt(
    payload: AssistantParseRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Extracts structured intent {service, date, time_pref, max_price, missing_fields}
    from natural language messages using LLM or local keyword/date fallback.
    """
    return await parse_assistant_message(message=payload.message, db=db)


@router.post("/suggest", response_model=AssistantSuggestResponse)
async def suggest_appointments(
    payload: AssistantSuggestRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Parses natural language requests and returns ranked candidate slots with explanations.
    If mandatory fields are missing, returns clarifying follow-up questions instead of guessing.
    NEVER creates a booking row; appointment creation happens only via normal POST /bookings.
    """
    return await suggest_assistant_slots(
        message=payload.message,
        db=db,
        service_id_override=payload.service_id,
        date_override=payload.date,
        time_pref_override=payload.time_pref,
        max_price_override=payload.max_price,
        current_user=current_user,
    )
