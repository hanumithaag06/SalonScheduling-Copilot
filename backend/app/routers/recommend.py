# Why: Recommendation router exposing GET /recommend.
# Fetches appointment availability, customer booking history, and applies the pure
# rule-based recommender engine to return the top 3 explainable slot recommendations.

from datetime import date, datetime, time, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_optional_current_user
from app.core.errors import NotFoundException
from app.db.session import get_db
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
    User,
    Service,
    Stylist,
    stylist_services,
    WorkingHours,
    TimeOff,
    Booking,
    SlotHold,
)
from app.schemas.recommend import RecommendationOut, ScoreBreakdownOut

router = APIRouter(prefix="/recommend", tags=["recommendations"])


def _ensure_utc(dt: datetime) -> datetime:
    """Normalizes naive or aware datetimes to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("", response_model=list[RecommendationOut])
async def get_recommended_slots(
    service_id: int = Query(..., description="ID of the service to book"),
    date: date = Query(..., alias="date", description="Target appointment date (YYYY-MM-DD)"),
    preferred_time: str | None = Query(
        default=None,
        description="Preferred time window: 'morning', 'afternoon', 'evening', or 'HH:MM'",
    ),
    max_price: Decimal | None = Query(default=None, description="Maximum budget filter"),
    lead_time_min: int = Query(default=30, ge=0, description="Minimum lead time in minutes"),
    buffer_min: int = Query(default=0, ge=0, description="Turnaround buffer in minutes"),
    top_n: int = Query(default=3, ge=1, le=10, description="Number of recommendations to return"),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the top 3 intelligent appointment recommendations with plain-language explanations.
    
    Scores each candidate slot based on:
    - Stylist loyalty: +3 max scaled by past bookings with that stylist
    - Time preference: +2 if within morning (<12:00), afternoon (12:00-17:00), or evening (>=17:00)
    - Specialization match: +1 if stylist specializes in this service
    - Gap filling: +1 if adjacent to existing appointments to minimize salon downtime
    """
    # 1. Fetch Service
    srv_stmt = select(Service).where(Service.id == service_id, Service.is_active.is_(True))
    service = (await db.execute(srv_stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found or inactive", code="SERVICE_NOT_FOUND")

    # 2. Check budget constraint
    if max_price is not None and service.price > max_price:
        return []

    # 3. Fetch eligible active stylists who offer this service
    st_stmt = (
        select(Stylist)
        .join(stylist_services, Stylist.id == stylist_services.c.stylist_id)
        .where(
            stylist_services.c.service_id == service_id,
            Stylist.is_active.is_(True),
        )
    )
    eligible_stylists = (await db.execute(st_stmt)).scalars().all()
    if not eligible_stylists:
        return []

    stylist_ids = [st.id for st in eligible_stylists]
    stylist_map = {st.id: st for st in eligible_stylists}
    stylist_info_list = [StylistInfo(id=st.id, name=st.name) for st in eligible_stylists]

    # 4. Day boundaries in UTC
    day_start = datetime.combine(date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(date, time.max, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)

    # 5. Fetch Working Shifts
    wh_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id.in_(stylist_ids),
        WorkingHours.weekday == date.weekday(),
    )
    wh_records = (await db.execute(wh_stmt)).scalars().all()
    working_shifts = [
        WorkingShift(
            stylist_id=wh.stylist_id,
            weekday=wh.weekday,
            start_time=wh.start_time,
            end_time=wh.end_time,
        )
        for wh in wh_records
    ]

    # 6. Fetch Time-Off
    to_stmt = select(TimeOff).where(
        TimeOff.stylist_id.in_(stylist_ids),
        TimeOff.start_ts < day_end,
        TimeOff.end_ts > day_start,
    )
    to_records = (await db.execute(to_stmt)).scalars().all()

    # 7. Fetch Confirmed Bookings
    bk_stmt = select(Booking).where(
        Booking.stylist_id.in_(stylist_ids),
        Booking.status == "confirmed",
        Booking.start_ts < day_end,
        Booking.end_ts > day_start,
    )
    bk_records = (await db.execute(bk_stmt)).scalars().all()

    # 8. Fetch Active Holds
    hold_stmt = select(SlotHold).where(
        SlotHold.stylist_id.in_(stylist_ids),
        SlotHold.expires_at > now_utc,
        SlotHold.start_ts < day_end,
        SlotHold.end_ts > day_start,
    )
    hold_records = (await db.execute(hold_stmt)).scalars().all()

    # 9. Compute Raw Available Slots per stylist using pure slot engine
    available_slots = []
    for st_info in stylist_info_list:
        st_shifts = [wh for wh in working_shifts if wh.stylist_id == st_info.id]
        st_time_off = [
            TimeInterval(start_ts=_ensure_utc(to.start_ts), end_ts=_ensure_utc(to.end_ts))
            for to in to_records
            if to.stylist_id == st_info.id
        ]
        st_bookings = [
            TimeInterval(start_ts=_ensure_utc(b.start_ts), end_ts=_ensure_utc(b.end_ts))
            for b in bk_records
            if b.stylist_id == st_info.id
        ]
        st_holds = [
            TimeInterval(start_ts=_ensure_utc(h.start_ts), end_ts=_ensure_utc(h.end_ts))
            for h in hold_records
            if h.stylist_id == st_info.id
        ]

        st_slots = find_available_slots(
            service_duration_min=service.duration_min,
            query_date=date,
            eligible_stylists=[st_info],
            working_hours=st_shifts,
            time_off=st_time_off,
            confirmed_bookings=st_bookings,
            active_holds=st_holds,
            current_time=now_utc,
            lead_time_min=lead_time_min,
            buffer_min=buffer_min,
            step_min=15,
        )
        available_slots.extend(st_slots)

    if not available_slots:
        return []

    # 10. Fetch Customer's Past Booking History (Loyalty) if logged in
    past_booking_counts: dict[int, int] = {}
    if current_user is not None:
        past_stmt = (
            select(Booking.stylist_id, func.count(Booking.id))
            .where(
                Booking.user_id == current_user.id,
                Booking.status.in_(["confirmed", "completed"]),
            )
            .group_by(Booking.stylist_id)
        )
        past_res = await db.execute(past_stmt)
        for st_id, count in past_res.all():
            past_booking_counts[st_id] = count

    # 11. Prepare Candidate Slots for Recommender
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

    # 12. Prepare Existing Bookings for Adjacency Evaluation
    existing_booking_objs = [
        ExistingBooking(
            stylist_id=bk.stylist_id,
            start_ts=_ensure_utc(bk.start_ts),
            end_ts=_ensure_utc(bk.end_ts),
        )
        for bk in bk_records
    ]

    # 13. Call Pure Recommendation Engine
    recommendations = recommend_slots(
        candidate_slots=candidate_slots,
        service_name=service.name,
        service_category=service.category,
        preferred_time=preferred_time,
        past_booking_counts=past_booking_counts,
        existing_bookings=existing_booking_objs,
        buffer_min=buffer_min,
        top_n=top_n,
    )

    # 14. Serialize to Pydantic Response
    return [
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
        for r in recommendations
    ]
