# Why: AI booking assistant service coordinating LLM intent extraction,
# fallback natural language parsing (rapidfuzz + dateparser), validation/sanitization,
# and slot recommendation integration. Guarantees that the assistant NEVER creates bookings.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import json
import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.engine.intent_parser import (
    DEFAULT_SERVICE_CATALOG,
    parse_booking_intent,
    ExtractedIntent,
)
from app.engine.slot_engine import (
    find_available_slots,
    StylistInfo,
    WorkingShift,
    TimeInterval,
)
from app.engine.recommender import (
    recommend_slots,
    CandidateSlot,
    ExistingBooking,
)
from app.models import (
    Service,
    Stylist,
    stylist_services,
    WorkingHours,
    TimeOff,
    Booking,
    SlotHold,
    User,
)
from app.schemas.assistant import AssistantParseResponse, AssistantSuggestResponse
from app.schemas.recommend import RecommendationOut, ScoreBreakdownOut

logger = logging.getLogger("stylify.assistant")


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def get_service_catalog(db: AsyncSession) -> list[dict]:
    """Fetches active services from DB to feed the intent matching catalog."""
    stmt = select(Service).where(Service.is_active.is_(True))
    services = (await db.execute(stmt)).scalars().all()
    if not services:
        return DEFAULT_SERVICE_CATALOG

    return [
        {
            "id": s.id,
            "name": s.name,
            "price": s.price,
            "duration_min": s.duration_min,
            "category": s.category,
        }
        for s in services
    ]


async def extract_intent_llm(
    message: str,
    catalog: list[dict],
) -> tuple[ExtractedIntent, str]:
    """
    Calls configured LLM to extract JSON intent.
    Falls back gracefully to rapidfuzz + dateparser if no key, timeout, or invalid JSON.
    """
    if not settings.LLM_API_KEY:
        # No key exists: use pure Python keyword/date parser fallback
        extracted = parse_booking_intent(message, catalog=catalog)
        return extracted, "keyword_fallback"

    today_iso = datetime.now(timezone.utc).date().isoformat()
    service_names = [s["name"] for s in catalog]

    system_prompt = (
        "You are an intent extraction engine for a salon booking assistant.\n"
        "Extract the user's booking request into a single raw JSON object with these exact keys:\n"
        "{\n"
        '  "service": string or null,\n'
        '  "date": "YYYY-MM-DD" or null,\n'
        '  "time_pref": "morning" | "afternoon" | "evening" | "HH:MM" | null,\n'
        '  "max_price": number or null,\n'
        '  "missing_fields": list of missing required fields (["service"] and/or ["date"])\n'
        "}\n"
        f"Available salon services: {service_names}.\n"
        f"Reference today date: {today_iso}.\n"
        "Return ONLY valid raw JSON with no markdown backticks or conversational text."
    )

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.0,
            }
            response = await client.post(settings.LLM_API_URL, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                # Strip markdown code blocks if returned
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content)
                parsed_json = json.loads(content)

                # Sanitize and validate LLM output
                service_raw = parsed_json.get("service")
                date_raw = parsed_json.get("date")
                time_raw = parsed_json.get("time_pref")
                budget_raw = parsed_json.get("max_price")

                # Match service against catalog
                srv_name = None
                srv_id = None
                if service_raw:
                    for s in catalog:
                        if s["name"].lower() == service_raw.lower():
                            srv_name = s["name"]
                            srv_id = s["id"]
                            break

                # Validate date
                target_date = None
                if date_raw:
                    try:
                        parsed_d = date.fromisoformat(date_raw)
                        if parsed_d >= datetime.now(timezone.utc).date():
                            target_date = parsed_d
                    except ValueError:
                        pass

                # Validate budget
                budget = None
                if budget_raw is not None:
                    try:
                        b_val = Decimal(str(budget_raw))
                        if b_val > 0:
                            budget = b_val
                    except Exception:
                        pass

                missing: list[str] = []
                if not srv_name:
                    missing.append("service")
                if not target_date:
                    missing.append("date")

                follow_up = None
                if "service" in missing and "date" in missing:
                    follow_up = "Which service would you like to book, and on what date?"
                elif "service" in missing:
                    follow_up = f"Which salon service would you like to book for {target_date}?"
                elif "date" in missing:
                    follow_up = f"What date would you like to schedule your {srv_name}?"

                return ExtractedIntent(
                    service_name=srv_name,
                    service_id=srv_id,
                    date=target_date,
                    time_pref=time_raw if time_raw in ("morning", "afternoon", "evening") or (time_raw and ":" in time_raw) else None,
                    max_price=budget,
                    missing_fields=missing,
                    follow_up_question=follow_up,
                ), "llm"

    except Exception as exc:
        logger.warning(f"LLM extraction failed or timed out: {exc}. Falling back to keyword parser.")

    # Fallback to local regex/rapidfuzz/dateparser engine
    extracted = parse_booking_intent(message, catalog=catalog)
    return extracted, "keyword_fallback"


async def parse_assistant_message(
    message: str,
    db: AsyncSession,
) -> AssistantParseResponse:
    """Parses a natural language booking prompt into standardized intent."""
    catalog = await get_service_catalog(db)
    intent, source = await extract_intent_llm(message, catalog=catalog)

    return AssistantParseResponse(
        service=intent.service_name,
        service_id=intent.service_id,
        date=intent.date,
        time_pref=intent.time_pref,
        max_price=intent.max_price,
        missing_fields=intent.missing_fields,
        follow_up_question=intent.follow_up_question,
        source=source,
    )


async def suggest_assistant_slots(
    message: str,
    db: AsyncSession,
    service_id_override: int | None = None,
    date_override: date | None = None,
    time_pref_override: str | None = None,
    max_price_override: Decimal | None = None,
    current_user: User | None = None,
) -> AssistantSuggestResponse:
    """
    Main assistant workflow: parses intent, validates constraints, invokes slot engine
    and recommender, and returns explainable slot options.
    NEVER creates a booking row in the database.
    """
    # 1. Parse or apply overrides
    parsed = await parse_assistant_message(message, db=db)

    active_service_id = service_id_override or parsed.service_id
    active_date = date_override or parsed.date
    active_time_pref = time_pref_override or parsed.time_pref
    active_max_price = max_price_override or parsed.max_price

    # 2. Check if mandatory fields are missing
    missing: list[str] = []
    if not active_service_id:
        missing.append("service")
    if not active_date:
        missing.append("date")

    if missing:
        follow_up = parsed.follow_up_question
        if not follow_up:
            if "service" in missing and "date" in missing:
                follow_up = "What service would you like to book, and on what date? (e.g. 'Haircut tomorrow afternoon')"
            elif "service" in missing:
                follow_up = f"Which salon service would you like to book for {active_date}?"
            else:
                follow_up = "What date would you like to schedule your appointment?"

        return AssistantSuggestResponse(
            intent=parsed,
            follow_up_question=follow_up,
            suggestions=[],
            message=follow_up,
        )

    # 3. Retrieve service
    srv_stmt = select(Service).where(Service.id == active_service_id, Service.is_active.is_(True))
    service = (await db.execute(srv_stmt)).scalar_one_or_none()
    if not service:
        return AssistantSuggestResponse(
            intent=parsed,
            follow_up_question=None,
            suggestions=[],
            message=f"Service ID #{active_service_id} was not found or is currently unavailable.",
        )

    # 4. Check budget filter
    if active_max_price is not None and service.price > active_max_price:
        return AssistantSuggestResponse(
            intent=parsed,
            follow_up_question=None,
            suggestions=[],
            message=(
                f"The requested service '{service.name}' costs ${service.price}, "
                f"which exceeds your budget of ${active_max_price}."
            ),
        )

    # 5. Fetch eligible active stylists who offer this service
    st_stmt = (
        select(Stylist)
        .join(stylist_services, Stylist.id == stylist_services.c.stylist_id)
        .where(stylist_services.c.service_id == service.id, Stylist.is_active.is_(True))
    )
    eligible_stylists = (await db.execute(st_stmt)).scalars().all()
    if not eligible_stylists:
        return AssistantSuggestResponse(
            intent=parsed,
            follow_up_question=None,
            suggestions=[],
            message=f"No active stylists currently perform '{service.name}'.",
        )

    stylist_ids = [st.id for st in eligible_stylists]
    stylist_map = {st.id: st for st in eligible_stylists}
    stylist_info_list = [StylistInfo(id=st.id, name=st.name) for st in eligible_stylists]

    # 6. Fetch shifts, time off, bookings, holds for that day
    day_start = datetime.combine(active_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(active_date, time.max, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)

    wh_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id.in_(stylist_ids),
        WorkingHours.weekday == active_date.weekday(),
    )
    working_shifts = [
        WorkingShift(
            stylist_id=wh.stylist_id,
            weekday=wh.weekday,
            start_time=wh.start_time,
            end_time=wh.end_time,
        )
        for wh in (await db.execute(wh_stmt)).scalars().all()
    ]

    to_stmt = select(TimeOff).where(
        TimeOff.stylist_id.in_(stylist_ids),
        TimeOff.start_ts < day_end,
        TimeOff.end_ts > day_start,
    )
    to_records = (await db.execute(to_stmt)).scalars().all()

    bk_stmt = select(Booking).where(
        Booking.stylist_id.in_(stylist_ids),
        Booking.status == "confirmed",
        Booking.start_ts < day_end,
        Booking.end_ts > day_start,
    )
    bk_records = (await db.execute(bk_stmt)).scalars().all()

    hold_stmt = select(SlotHold).where(
        SlotHold.stylist_id.in_(stylist_ids),
        SlotHold.expires_at > now_utc,
        SlotHold.start_ts < day_end,
        SlotHold.end_ts > day_start,
    )
    hold_records = (await db.execute(hold_stmt)).scalars().all()

    # 7. Compute available slots per stylist
    available_slots = []
    for st_info in stylist_info_list:
        st_shifts = [wh for wh in working_shifts if wh.stylist_id == st_info.id]
        st_time_off = [
            TimeInterval(start_ts=_ensure_utc(to.start_ts), end_ts=_ensure_utc(to.end_ts))
            for to in to_records if to.stylist_id == st_info.id
        ]
        st_bookings = [
            TimeInterval(start_ts=_ensure_utc(b.start_ts), end_ts=_ensure_utc(b.end_ts))
            for b in bk_records if b.stylist_id == st_info.id
        ]
        st_holds = [
            TimeInterval(start_ts=_ensure_utc(h.start_ts), end_ts=_ensure_utc(h.end_ts))
            for h in hold_records if h.stylist_id == st_info.id
        ]

        st_slots = find_available_slots(
            service_duration_min=service.duration_min,
            query_date=active_date,
            eligible_stylists=[st_info],
            working_hours=st_shifts,
            time_off=st_time_off,
            confirmed_bookings=st_bookings,
            active_holds=st_holds,
            current_time=now_utc,
            lead_time_min=30,
            buffer_min=0,
            step_min=15,
        )
        available_slots.extend(st_slots)

    if not available_slots:
        return AssistantSuggestResponse(
            intent=parsed,
            follow_up_question=None,
            suggestions=[],
            message=f"No available slots found for {service.name} on {active_date}. Please try another date.",
        )

    # 8. User loyalty past booking counts
    past_counts: dict[int, int] = {}
    if current_user:
        past_stmt = select(Booking.stylist_id, Booking.id).where(
            Booking.user_id == current_user.id,
            Booking.status.in_(["confirmed", "completed"]),
        )
        for st_id, _ in (await db.execute(past_stmt)).all():
            past_counts[st_id] = past_counts.get(st_id, 0) + 1

    candidate_slots = [
        CandidateSlot(
            stylist_id=slot.stylist_id,
            stylist_name=slot.stylist_name,
            stylist_specialization=stylist_map[slot.stylist_id].specialization,
            start_ts=slot.start_ts,
            end_ts=slot.end_ts,
            price=service.price,
        )
        for slot in available_slots
    ]

    existing_booking_objs = [
        ExistingBooking(
            stylist_id=b.stylist_id,
            start_ts=_ensure_utc(b.start_ts),
            end_ts=_ensure_utc(b.end_ts),
        )
        for b in bk_records
    ]

    # 9. Rank with pure recommender
    ranked_recs = recommend_slots(
        candidate_slots=candidate_slots,
        service_name=service.name,
        service_category=service.category,
        preferred_time=active_time_pref,
        past_booking_counts=past_counts,
        existing_bookings=existing_booking_objs,
        top_n=3,
    )

    out_suggestions = [
        RecommendationOut(
            stylist_id=r.stylist_id,
            stylist_name=r.stylist_name,
            stylist_specialization=r.stylist_specialization,
            start_ts=r.start_ts,
            end_ts=r.end_ts,
            duration_min=r.duration_min,
            price=r.price,
            score=r.score,
            score_breakdown=ScoreBreakdownOut(
                past_bookings=r.score_breakdown.past_bookings,
                preferred_time=r.score_breakdown.preferred_time,
                specialization=r.score_breakdown.specialization,
                adjacent_booking=r.score_breakdown.adjacent_booking,
            ),
            reason=r.reason,
        )
        for r in ranked_recs
    ]

    return AssistantSuggestResponse(
        intent=parsed,
        follow_up_question=None,
        suggestions=out_suggestions,
        message=f"I found {len(out_suggestions)} great options for your {service.name} on {active_date}.",
    )
