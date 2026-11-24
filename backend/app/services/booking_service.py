# Why: Core booking business logic and validation service.
# Enforces all salon integrity rules: lead times, stylist-service mappings,
# customer overlap guards, max active bookings, 2-hour cancellation windows,
# write-time availability re-checks, asyncio mutex guard, and audit trail logging.

import asyncio
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ForbiddenException,
)
from app.models import (
    Booking, Service, Stylist, stylist_services,
    WorkingHours, TimeOff, SlotHold, AuditLog, User
)
from app.schemas.booking import BookingCreate, BookingReschedule

MAX_ACTIVE_BOOKINGS_PER_USER = 5
MIN_CANCELLATION_WINDOW_HOURS = 2

# Process-level mutex to serialize critical write-time availability re-checks
_booking_lock = asyncio.Lock()


def _ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime is timezone-aware in UTC (guards against naive SQLite loads)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def create_booking(
    payload: BookingCreate,
    user: User,
    db: AsyncSession,
) -> Booking:
    """
    Creates a new confirmed appointment after validating all business constraints.
    Re-checks availability at write time and relies on the database exclusion constraint
    as the final guard against concurrent double-booking.
    """
    now_utc = datetime.now(timezone.utc)
    start_ts = _ensure_utc(payload.start_ts)

    # 1. Start time must not be in the past
    if start_ts <= now_utc:
        raise BadRequestException(
            detail="Cannot book an appointment in the past",
            code="PAST_SLOT"
        )

    # 2. Check maximum active bookings per customer
    active_count_stmt = select(func.count()).select_from(Booking).where(
        Booking.user_id == user.id,
        Booking.status == "confirmed"
    )
    active_count = (await db.execute(active_count_stmt)).scalar_one()
    if active_count >= MAX_ACTIVE_BOOKINGS_PER_USER:
        raise BadRequestException(
            detail=f"Maximum active bookings limit reached ({MAX_ACTIVE_BOOKINGS_PER_USER})",
            code="MAX_ACTIVE_BOOKINGS"
        )

    # 3. Verify Service exists and is active
    srv_stmt = select(Service).where(Service.id == payload.service_id, Service.is_active.is_(True))
    service = (await db.execute(srv_stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found or inactive", code="SERVICE_NOT_FOUND")

    # 4. Verify Stylist exists and is active
    st_stmt = select(Stylist).where(Stylist.id == payload.stylist_id, Stylist.is_active.is_(True))
    stylist = (await db.execute(st_stmt)).scalar_one_or_none()
    if not stylist:
        raise NotFoundException(detail="Stylist not found or inactive", code="STYLIST_NOT_FOUND")

    # 5. Verify Stylist performs the requested service
    map_stmt = select(stylist_services).where(
        stylist_services.c.stylist_id == payload.stylist_id,
        stylist_services.c.service_id == payload.service_id
    )
    if not (await db.execute(map_stmt)).first():
        raise BadRequestException(
            detail="The selected stylist does not offer this service",
            code="INVALID_STYLIST_SERVICE"
        )

    end_ts = start_ts + timedelta(minutes=service.duration_min)

    # 6. Verify Shift boundary
    wh_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id == payload.stylist_id,
        WorkingHours.weekday == start_ts.weekday()
    )
    wh = (await db.execute(wh_stmt)).scalar_one_or_none()
    if not wh:
        raise BadRequestException(
            detail="Stylist does not work on this day",
            code="OUTSIDE_WORKING_HOURS"
        )

    if start_ts.time() < wh.start_time or end_ts.time() > wh.end_time:
        raise BadRequestException(
            detail="Appointment slot falls outside stylist working hours",
            code="OUTSIDE_WORKING_HOURS"
        )

    # 7. Check Stylist Time Off
    to_stmt = select(TimeOff).where(
        TimeOff.stylist_id == payload.stylist_id,
        TimeOff.start_ts < end_ts,
        TimeOff.end_ts > start_ts
    )
    if (await db.execute(to_stmt)).scalar_one_or_none():
        raise ConflictException(
            detail="Stylist is on scheduled time-off during this slot",
            code="STYLIST_UNAVAILABLE"
        )

    # 8. Check customer does not have another overlapping confirmed appointment
    user_overlap_stmt = select(Booking).where(
        Booking.user_id == user.id,
        Booking.status == "confirmed",
        Booking.start_ts < end_ts,
        Booking.end_ts > start_ts
    )
    if (await db.execute(user_overlap_stmt)).scalar_one_or_none():
        raise ConflictException(
            detail="You already have another confirmed appointment at this time",
            code="USER_OVERLAP"
        )

    # Critical section protected by mutex + write-time DB verification
    async with _booking_lock:
        # 9. Write-time availability re-check for stylist
        stylist_overlap_stmt = select(Booking).where(
            Booking.stylist_id == payload.stylist_id,
            Booking.status == "confirmed",
            Booking.start_ts < end_ts,
            Booking.end_ts > start_ts
        )
        if (await db.execute(stylist_overlap_stmt)).scalar_one_or_none():
            raise ConflictException(
                detail="The selected time slot is already booked",
                code="SLOT_TAKEN"
            )

        # 10. Check if slot is held by another user
        hold_stmt = select(SlotHold).where(
            SlotHold.stylist_id == payload.stylist_id,
            SlotHold.user_id != user.id,
            SlotHold.expires_at > now_utc,
            SlotHold.start_ts < end_ts,
            SlotHold.end_ts > start_ts
        )
        if (await db.execute(hold_stmt)).scalar_one_or_none():
            raise ConflictException(
                detail="The selected time slot is temporarily on hold by another customer",
                code="SLOT_HELD"
            )

        # 11. Create Booking entity
        booking = Booking(
            user_id=user.id,
            service_id=payload.service_id,
            stylist_id=payload.stylist_id,
            start_ts=start_ts,
            end_ts=end_ts,
            status="confirmed",
            notes=payload.notes,
        )
        db.add(booking)
        await db.flush()

        # 12. Create Audit Log entry
        audit = AuditLog(
            actor_id=user.id,
            action="CREATE",
            entity="booking",
            entity_id=booking.id,
            details=json.dumps({
                "service_id": payload.service_id,
                "stylist_id": payload.stylist_id,
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
            })
        )
        db.add(audit)

        # 13. Commit with database-level exclusion constraint error handling
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ConflictException(
                detail="The selected time slot is already booked",
                code="SLOT_TAKEN"
            )

    # Fetch loaded booking for response
    res = await db.execute(
        select(Booking)
        .options(selectinload(Booking.service), selectinload(Booking.stylist))
        .where(Booking.id == booking.id)
    )
    return res.scalar_one()


async def reschedule_booking(
    booking_id: int,
    payload: BookingReschedule,
    user: User,
    db: AsyncSession,
) -> Booking:
    """
    Reschedules an existing confirmed booking to a new start time.
    Enforces a minimum 2-hour window and re-checks availability.
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch booking
    b_stmt = (
        select(Booking)
        .options(selectinload(Booking.service), selectinload(Booking.stylist))
        .where(Booking.id == booking_id)
    )
    booking = (await db.execute(b_stmt)).scalar_one_or_none()
    if not booking:
        raise NotFoundException(detail="Booking not found", code="BOOKING_NOT_FOUND")

    # Only owner or admin can reschedule
    if booking.user_id != user.id and user.role != "admin":
        raise ForbiddenException(detail="Cannot reschedule another user's booking", code="FORBIDDEN")

    if booking.status != "confirmed":
        raise BadRequestException(
            detail=f"Cannot reschedule a booking with status '{booking.status}'",
            code="INVALID_BOOKING_STATUS"
        )

    # 2. Enforce 2-hour reschedule window
    if _ensure_utc(booking.start_ts) - now_utc < timedelta(hours=MIN_CANCELLATION_WINDOW_HOURS):
        raise BadRequestException(
            detail=f"Bookings cannot be rescheduled within {MIN_CANCELLATION_WINDOW_HOURS} hours of start time",
            code="RESCHEDULE_WINDOW_EXPIRED"
        )

    new_start_ts = _ensure_utc(payload.new_start_ts)
    if new_start_ts <= now_utc:
        raise BadRequestException(
            detail="New start time cannot be in the past",
            code="PAST_SLOT"
        )

    # 3. Calculate new end timestamp
    duration_min = booking.service.duration_min
    new_end_ts = new_start_ts + timedelta(minutes=duration_min)

    # 4. Check working hours on new date
    wh_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id == booking.stylist_id,
        WorkingHours.weekday == new_start_ts.weekday()
    )
    wh = (await db.execute(wh_stmt)).scalar_one_or_none()
    if not wh or new_start_ts.time() < wh.start_time or new_end_ts.time() > wh.end_time:
        raise BadRequestException(
            detail="New appointment slot falls outside stylist working hours",
            code="OUTSIDE_WORKING_HOURS"
        )

    # 5. Check stylist time-off on new slot
    to_stmt = select(TimeOff).where(
        TimeOff.stylist_id == booking.stylist_id,
        TimeOff.start_ts < new_end_ts,
        TimeOff.end_ts > new_start_ts
    )
    if (await db.execute(to_stmt)).scalar_one_or_none():
        raise ConflictException(
            detail="Stylist is on scheduled time-off during this new slot",
            code="STYLIST_UNAVAILABLE"
        )

    # Critical section protected by lock
    async with _booking_lock:
        # 6. Check stylist slot availability (excluding this booking)
        st_overlap_stmt = select(Booking).where(
            Booking.stylist_id == booking.stylist_id,
            Booking.id != booking.id,
            Booking.status == "confirmed",
            Booking.start_ts < new_end_ts,
            Booking.end_ts > new_start_ts
        )
        if (await db.execute(st_overlap_stmt)).scalar_one_or_none():
            raise ConflictException(
                detail="The new time slot is already booked",
                code="SLOT_TAKEN"
            )

        # 7. Check customer overlap on new slot
        user_overlap_stmt = select(Booking).where(
            Booking.user_id == booking.user_id,
            Booking.id != booking.id,
            Booking.status == "confirmed",
            Booking.start_ts < new_end_ts,
            Booking.end_ts > new_start_ts
        )
        if (await db.execute(user_overlap_stmt)).scalar_one_or_none():
            raise ConflictException(
                detail="You already have another confirmed appointment during this new time",
                code="USER_OVERLAP"
            )

        # 8. Update booking
        old_start = booking.start_ts.isoformat()
        booking.start_ts = new_start_ts
        booking.end_ts = new_end_ts
        if payload.notes is not None:
            booking.notes = payload.notes

        # 9. Audit Log
        audit = AuditLog(
            actor_id=user.id,
            action="RESCHEDULE",
            entity="booking",
            entity_id=booking.id,
            details=json.dumps({
                "old_start_ts": old_start,
                "new_start_ts": new_start_ts.isoformat(),
                "new_end_ts": new_end_ts.isoformat(),
            })
        )
        db.add(audit)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ConflictException(
                detail="The selected time slot is already booked",
                code="SLOT_TAKEN"
            )

    await db.refresh(booking)
    return booking


async def cancel_booking(
    booking_id: int,
    user: User,
    db: AsyncSession,
) -> Booking:
    """
    Cancels a confirmed appointment. Enforces 2-hour minimum cancellation window.
    Logs audit event and frees the slot.
    """
    now_utc = datetime.now(timezone.utc)

    b_stmt = (
        select(Booking)
        .options(selectinload(Booking.service), selectinload(Booking.stylist))
        .where(Booking.id == booking_id)
    )
    booking = (await db.execute(b_stmt)).scalar_one_or_none()
    if not booking:
        raise NotFoundException(detail="Booking not found", code="BOOKING_NOT_FOUND")

    if booking.user_id != user.id and user.role != "admin":
        raise ForbiddenException(detail="Cannot cancel another user's booking", code="FORBIDDEN")

    if booking.status != "confirmed":
        raise BadRequestException(
            detail=f"Cannot cancel a booking with status '{booking.status}'",
            code="INVALID_BOOKING_STATUS"
        )

    # Enforce 2-hour cancellation window
    if _ensure_utc(booking.start_ts) - now_utc < timedelta(hours=MIN_CANCELLATION_WINDOW_HOURS):
        raise BadRequestException(
            detail=f"Bookings cannot be cancelled within {MIN_CANCELLATION_WINDOW_HOURS} hours of start time",
            code="CANCELLATION_WINDOW_EXPIRED"
        )

    booking.status = "cancelled"

    # Audit Log
    audit = AuditLog(
        actor_id=user.id,
        action="CANCEL",
        entity="booking",
        entity_id=booking.id,
        details=json.dumps({"cancelled_at": now_utc.isoformat()})
    )
    db.add(audit)

    await db.commit()
    await db.refresh(booking)
    return booking
