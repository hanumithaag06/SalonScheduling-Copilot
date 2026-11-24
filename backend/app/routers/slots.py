# Why: Slot discovery router exposing GET /slots.
# Queries DB constraints, passes pure data to slot_engine, and returns available slots.

from datetime import date, datetime, time, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException
from app.db.session import get_db
from app.engine.slot_engine import (
    find_available_slots,
    StylistInfo,
    WorkingShift,
    TimeInterval,
)
from app.models import Service, Stylist, stylist_services, WorkingHours, TimeOff, Booking, SlotHold
from app.schemas.slot import SlotOut

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("", response_model=list[SlotOut])
async def get_available_slots(
    service_id: int = Query(..., description="ID of the service to book"),
    date: date = Query(..., alias="date", description="Target appointment date (YYYY-MM-DD)"),
    stylist_id: int | None = Query(default=None, description="Optional stylist filter"),
    max_price: Decimal | None = Query(default=None, description="Maximum budget filter"),
    lead_time_min: int = Query(default=30, ge=0, description="Minimum lead time in minutes"),
    buffer_min: int = Query(default=0, ge=0, description="Buffer turnaround minutes after booking"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns available appointment slots in 15-minute increments for a given service and date.
    Respects stylist shifts, lead times, post-booking buffers, active holds, and existing bookings.
    """
    # 1. Fetch Service
    srv_stmt = select(Service).where(Service.id == service_id, Service.is_active.is_(True))
    service = (await db.execute(srv_stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found or inactive", code="SERVICE_NOT_FOUND")

    # 2. Check max_price budget constraint
    if max_price is not None and service.price > max_price:
        return []

    # 3. Find eligible active stylists who perform this service
    st_stmt = (
        select(Stylist)
        .join(stylist_services, Stylist.id == stylist_services.c.stylist_id)
        .where(
            stylist_services.c.service_id == service_id,
            Stylist.is_active.is_(True)
        )
    )
    if stylist_id is not None:
        st_stmt = st_stmt.where(Stylist.id == stylist_id)

    eligible_stylists = (await db.execute(st_stmt)).scalars().all()
    if not eligible_stylists:
        return []

    stylist_ids = [st.id for st in eligible_stylists]
    stylist_info_list = [StylistInfo(id=st.id, name=st.name) for st in eligible_stylists]

    # 4. Day boundaries in UTC
    day_start = datetime.combine(date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(date, time.max, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)

    # 5. Fetch Working Hours for the target weekday
    wh_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id.in_(stylist_ids),
        WorkingHours.weekday == date.weekday()
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

    # 6. Fetch Time Off / Holidays overlapping the day
    to_stmt = select(TimeOff).where(
        TimeOff.stylist_id.in_(stylist_ids),
        TimeOff.start_ts < day_end,
        TimeOff.end_ts > day_start
    )
    to_records = (await db.execute(to_stmt)).scalars().all()
    time_off_intervals = [
        TimeInterval(start_ts=to.start_ts, end_ts=to.end_ts)
        for to in to_records
    ]

    # 7. Fetch Confirmed Bookings overlapping the day
    bk_stmt = select(Booking).where(
        Booking.stylist_id.in_(stylist_ids),
        Booking.status == "confirmed",
        Booking.start_ts < day_end,
        Booking.end_ts > day_start
    )
    bk_records = (await db.execute(bk_stmt)).scalars().all()
    booking_intervals = [
        TimeInterval(start_ts=b.start_ts, end_ts=b.end_ts)
        for b in bk_records
    ]

    # 8. Fetch Active Holds (expires_at > now) overlapping the day
    hd_stmt = select(SlotHold).where(
        SlotHold.stylist_id.in_(stylist_ids),
        SlotHold.expires_at > now_utc,
        SlotHold.start_ts < day_end,
        SlotHold.end_ts > day_start
    )
    hd_records = (await db.execute(hd_stmt)).scalars().all()
    hold_intervals = [
        TimeInterval(start_ts=h.start_ts, end_ts=h.end_ts)
        for h in hd_records
    ]

    # 9. Execute pure slot calculation engine
    raw_slots = find_available_slots(
        service_duration_min=service.duration_min,
        query_date=date,
        eligible_stylists=stylist_info_list,
        working_hours=working_shifts,
        time_off=time_off_intervals,
        confirmed_bookings=booking_intervals,
        active_holds=hold_intervals,
        current_time=now_utc,
        lead_time_min=lead_time_min,
        buffer_min=buffer_min,
        step_min=15,
    )

    # 10. Map to Pydantic responses with price
    return [
        SlotOut(
            stylist_id=s.stylist_id,
            stylist_name=s.stylist_name,
            start_ts=s.start_ts,
            end_ts=s.end_ts,
            duration_min=s.duration_min,
            price=service.price,
        )
        for s in raw_slots
    ]
